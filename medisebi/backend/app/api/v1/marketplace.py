"""
MediSebi — Inter-Dispensary Marketplace API
=============================================
A marketplace for pharmacies to sell medicines nearing expiry to other shops
that need them. Built on top of the existing StockTransferRequest model.

Endpoints:
    GET  /marketplace/expiring-listings    — Find medicines expiring within 60 days across all shops
    GET  /marketplace/demand-matches       — Find shops that NEED expiring medicines
    POST /marketplace/create-offer         — Create a sell offer from one shop to another
    GET  /marketplace/offers               — List all marketplace offers
    PUT  /marketplace/offers/{id}/accept   — Buyer accepts a marketplace offer
    PUT  /marketplace/offers/{id}/reject   — Buyer rejects a marketplace offer
    PUT  /marketplace/offers/{id}/complete — Mark a completed transfer
    GET  /marketplace/dashboard            — Marketplace summary for the dashboard
    GET  /marketplace/shop/{shop_id}/listings      — This shop's sellable listings
    GET  /marketplace/shop/{shop_id}/opportunities — Items this shop can buy
"""

import json
from datetime import datetime, timezone, date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_client_info, require_role
from app.core.audit_hash import compute_audit_hash
from app.models.user import User, UserRole
from app.models.salt import Salt
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.shop import Shop
from app.models.stock_transfer import (
    StockTransferRequest,
    TransferStatus,
    TransferPriority,
)
from app.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationSource,
)
from app.models.audit_log import AuditLog, ActionType

router = APIRouter(tags=["Marketplace"])

MARKETPLACE_REASON_PREFIX = "Marketplace offer"


# ── Helpers ─────────────────────────────────────────────────────

def _create_audit_log(
    db: Session,
    action_type: ActionType,
    user_id: int,
    description: str,
    details: dict,
    resource_type: str,
    resource_id: int,
    client_info: dict,
) -> None:
    """Create an audit log entry with computed hash."""
    now = datetime.now(timezone.utc).isoformat()
    details_str = json.dumps(details, default=str)
    audit = AuditLog(
        action_type=action_type,
        description=description,
        details=details_str,
        user_id=user_id,
        ip_address=client_info.get("ip_address"),
        user_agent=client_info.get("user_agent"),
        resource_type=resource_type,
        resource_id=resource_id,
        sha256_hash=compute_audit_hash(
            action_type=action_type.value,
            user_id=user_id,
            timestamp=now,
            details=details_str,
            resource_type=resource_type,
            resource_id=resource_id,
        ),
    )
    db.add(audit)


def _create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    severity: NotificationSeverity,
    source: NotificationSource,
    resource_type: str | None = None,
    resource_id: int | None = None,
) -> Notification:
    """Create an in-app notification."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        source=source,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notif)
    db.flush()
    return notif


def _get_shop_users(db: Session, shop_id: int) -> list[User]:
    """Get all active users assigned to a shop (admin + pharmacists)."""
    users = db.execute(
        select(User)
        .join(User.shop_assignments)  # type: ignore[attr-defined]
        .where(User.is_active == True)
    ).scalars().all()
    # Also include all admins (they see everything)
    admins = db.execute(
        select(User).where(User.role == UserRole.ADMIN, User.is_active == True)
    ).scalars().all()
    seen = {u.id for u in users}
    for a in admins:
        if a.id not in seen:
            users.append(a)
    return users


def _compute_suggested_discount(expiry_date: date) -> int:
    """Compute suggested discount percentage based on days until expiry."""
    today = date.today()
    delta = (expiry_date - today).days

    if delta < 0:
        return 40  # expired
    elif delta < 7:
        return 30  # < 7 days
    elif delta < 15:
        return 20  # < 15 days
    elif delta < 30:
        return 10  # < 30 days
    return 0  # 30-60 days, no discount needed yet


def _get_expiring_items(db: Session, days: int = 60) -> list[dict]:
    """Get inventory items expiring within the given days across all shops."""
    today = date.today()
    cutoff = today + timedelta(days=days)

    items = db.execute(
        select(Inventory)
        .where(
            Inventory.expiry_date <= cutoff,
            Inventory.quantity > 0,
            Inventory.is_reserved == False,
        )
        .order_by(Inventory.expiry_date.asc())
    ).scalars().all()

    results = []
    for inv in items:
        delta = (inv.expiry_date - today).days
        results.append({
            "inventory": inv,
            "medicine": inv.medicine,
            "shop": inv.shop,
            "days_until_expiry": delta,
            "suggested_discount_pct": _compute_suggested_discount(inv.expiry_date),
        })

    return results


# ── Pydantic Schemas ────────────────────────────────────────────

class ExpiringListingItem(BaseModel):
    """Schema for an expiring listing item."""
    inventory_id: int
    shop_name: str
    shop_id: int
    medicine_name: str
    salt_name: str | None
    quantity: int
    expiry_date: date
    days_until_expiry: int
    unit_price: float | None
    suggested_discount_pct: int


class DemandMatchItem(BaseModel):
    """Schema for a demand match."""
    source_inventory_id: int
    source_shop_name: str
    source_shop_id: int
    medicine_name: str
    salt_name: str | None
    salt_id: int
    available_quantity: int
    expiry_date: date
    days_until_expiry: int
    dest_shop_name: str
    dest_shop_id: int
    deficit_quantity: int
    suggested_discount_pct: int
    priority_score: float


class CreateOfferRequest(BaseModel):
    """Schema for creating a marketplace sell offer."""
    from_shop_id: int = Field(..., gt=0, description="Shop selling the medicine")
    to_shop_id: int = Field(..., gt=0, description="Shop buying the medicine")
    inventory_id: int = Field(..., gt=0, description="Inventory batch to sell")
    quantity: int = Field(..., gt=0, description="Quantity to sell")
    offered_price: float = Field(..., ge=0, description="Price per unit offered")
    notes: str = Field("", description="Optional notes for the buyer")


class OfferResponse(BaseModel):
    """Schema for a marketplace offer response."""
    id: int
    from_shop_id: int
    to_shop_id: int
    med_id: int
    inventory_id: int | None
    quantity_requested: int
    quantity_transferred: int | None
    reason: str | None
    priority: str
    status: str
    approved_by: int | None
    approved_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    from_shop_name: str | None = None
    to_shop_name: str | None = None
    medicine_name: str | None = None
    salt_name: str | None = None

    model_config = {"from_attributes": True}


class OfferListResponse(BaseModel):
    """Paginated list of marketplace offers."""
    items: list[OfferResponse]
    total: int
    page: int
    size: int


class RejectOfferRequest(BaseModel):
    """Schema for rejecting a marketplace offer."""
    reason: str = Field(..., min_length=3, description="Reason for rejection")


class TopExpiringItem(BaseModel):
    """Schema for a top expiring item in dashboard."""
    medicine_name: str
    salt_name: str | None
    shop_name: str
    days_until_expiry: int
    quantity: int
    suggested_discount_pct: int


class ShopActivityItem(BaseModel):
    """Schema for shop activity in dashboard."""
    listed: int
    received: int


class DashboardResponse(BaseModel):
    """Schema for marketplace dashboard summary."""
    total_expiring_items: int
    total_demand_matches: int
    offers_by_status: dict[str, int]
    top_expiring_medicines: list[TopExpiringItem]
    shop_activity: dict[str, ShopActivityItem]


# ── GET /marketplace/expiring-listings ─────────────────────────

@router.get(
    "/expiring-listings",
    response_model=list[ExpiringListingItem],
    summary="Find medicines expiring within 60 days",
)
def get_expiring_listings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(60, ge=1, le=365, description="Days within which items expire"),
):
    """Find medicines expiring within N days across ALL shops. Sorted by urgency."""
    items = _get_expiring_items(db, days=days)

    results = []
    for item in items:
        inv = item["inventory"]
        med = item["medicine"]
        shop = item["shop"]

        salt_name = None
        if med and med.salt:
            salt_name = med.salt.formula_name

        results.append(ExpiringListingItem(
            inventory_id=inv.id,
            shop_name=shop.name if shop else "Unknown",
            shop_id=inv.shop_id,
            medicine_name=med.brand_name if med else "Unknown",
            salt_name=salt_name,
            quantity=inv.quantity,
            expiry_date=inv.expiry_date,
            days_until_expiry=item["days_until_expiry"],
            unit_price=inv.selling_price,
            suggested_discount_pct=item["suggested_discount_pct"],
        ))

    return results


# ── GET /marketplace/demand-matches ────────────────────────────

@router.get(
    "/demand-matches",
    response_model=list[DemandMatchItem],
    summary="Find shops that need expiring medicines",
)
def get_demand_matches(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Find demand matches: expiring medicines that other shops need.
    For each expiring item, find shops whose inventory of the same salt
    is below reorder_level.
    """
    expiring_items = _get_expiring_items(db, days=60)

    # Get all shops
    all_shops = db.execute(
        select(Shop).where(Shop.is_active == True)
    ).scalars().all()

    matches: list[DemandMatchItem] = []

    for item in expiring_items:
        inv = item["inventory"]
        med = item["medicine"]

        if not med or not med.salt_id:
            continue

        salt = med.salt
        salt_id = med.salt_id

        # Find all medicines with the same salt
        related_meds = db.execute(
            select(Medicine).where(
                Medicine.salt_id == salt_id,
                Medicine.is_active == True,
            )
        ).scalars().all()

        related_med_ids = [m.id for m in related_meds]

        if not related_med_ids:
            continue

        # For each shop, check if they have low stock of any of these medicines
        for shop in all_shops:
            # Skip the shop that has the expiring stock
            if shop.id == inv.shop_id:
                continue

            # Sum all inventory for related medicines at this shop
            shop_qty = db.execute(
                select(func.coalesce(func.sum(Inventory.quantity), 0))
                .where(
                    Inventory.shop_id == shop.id,
                    Inventory.med_id.in_(related_med_ids),
                )
            ).scalar() or 0

            reorder_level = salt.reorder_level or 100  # default threshold

            if shop_qty < reorder_level:
                deficit = reorder_level - shop_qty
                # Priority score: lower days_until_expiry + higher deficit = higher priority
                priority_score = (60 - item["days_until_expiry"]) + (deficit / reorder_level * 30)

                salt_name = salt.formula_name if salt else None

                matches.append(DemandMatchItem(
                    source_inventory_id=inv.id,
                    source_shop_name=item["shop"].name if item["shop"] else "Unknown",
                    source_shop_id=inv.shop_id,
                    medicine_name=med.brand_name,
                    salt_name=salt_name,
                    salt_id=salt_id,
                    available_quantity=inv.quantity,
                    expiry_date=inv.expiry_date,
                    days_until_expiry=item["days_until_expiry"],
                    dest_shop_name=shop.name,
                    dest_shop_id=shop.id,
                    deficit_quantity=deficit,
                    suggested_discount_pct=item["suggested_discount_pct"],
                    priority_score=round(priority_score, 2),
                ))

    # Sort by priority score descending (highest priority first)
    matches.sort(key=lambda m: m.priority_score, reverse=True)

    return matches


# ── POST /marketplace/create-offer ─────────────────────────────

@router.post(
    "/create-offer",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a marketplace sell offer",
)
def create_offer(
    data: CreateOfferRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
):
    """
    Create a sell offer from one shop to another.
    Validates ownership, expiry window, and creates a StockTransferRequest.
    Admin/Pharmacist only.
    """
    # Validate from_shop
    from_shop = db.execute(
        select(Shop).where(Shop.id == data.from_shop_id, Shop.is_active == True)
    ).scalar_one_or_none()
    if not from_shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source shop with id={data.from_shop_id} not found or inactive",
        )

    # Validate to_shop
    to_shop = db.execute(
        select(Shop).where(Shop.id == data.to_shop_id, Shop.is_active == True)
    ).scalar_one_or_none()
    if not to_shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination shop with id={data.to_shop_id} not found or inactive",
        )

    if data.from_shop_id == data.to_shop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create an offer to the same shop",
        )

    # Validate inventory exists and belongs to from_shop
    inv = db.execute(
        select(Inventory).where(Inventory.id == data.inventory_id)
    ).scalar_one_or_none()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with id={data.inventory_id} not found",
        )

    if inv.shop_id != data.from_shop_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inventory does not belong to the source shop",
        )

    if inv.quantity < data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {inv.quantity}, Requested: {data.quantity}",
        )

    # Check expiry is within 60 days
    today = date.today()
    cutoff = today + timedelta(days=60)
    if inv.expiry_date > cutoff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marketplace offers are only for items expiring within 60 days",
        )

    # Build the reason string
    med = inv.medicine
    brand = med.brand_name if med else "Unknown"
    reason = (
        f"{MARKETPLACE_REASON_PREFIX}: {brand} expiring on "
        f"{inv.expiry_date.isoformat()}"
    )
    if data.notes:
        reason += f" — {data.notes}"

    # Determine priority based on expiry
    delta = (inv.expiry_date - today).days
    if delta < 7:
        priority = TransferPriority.CRITICAL
    elif delta < 15:
        priority = TransferPriority.HIGH
    elif delta < 30:
        priority = TransferPriority.MEDIUM
    else:
        priority = TransferPriority.LOW

    # Create StockTransferRequest
    transfer = StockTransferRequest(
        from_shop_id=data.from_shop_id,
        to_shop_id=data.to_shop_id,
        med_id=inv.med_id,
        inventory_id=inv.id,
        quantity_requested=data.quantity,
        reason=reason,
        priority=priority,
        status=TransferStatus.PENDING,
    )
    db.add(transfer)
    db.flush()

    # Reserve the inventory
    inv.is_reserved = True

    # Create audit log
    _create_audit_log(
        db=db,
        action_type=ActionType.STOCK_TRANSFERRED,
        user_id=current_user.id,
        description=(
            f"Marketplace offer created: {brand} ({data.quantity} units) "
            f"from {from_shop.name} to {to_shop.name}"
        ),
        details={
            "source": "marketplace",
            "transfer_id": transfer.id,
            "from_shop_id": data.from_shop_id,
            "to_shop_id": data.to_shop_id,
            "inventory_id": data.inventory_id,
            "med_id": inv.med_id,
            "quantity": data.quantity,
            "offered_price": data.offered_price,
        },
        resource_type="transfer_request",
        resource_id=transfer.id,
        client_info=client_info,
    )

    # Notify destination shop's users
    dest_users = _get_shop_users(db, data.to_shop_id)
    for user in dest_users:
        _create_notification(
            db=db,
            user_id=user.id,
            title=f"New Marketplace Offer: {brand}",
            message=(
                f"{from_shop.name} is offering {data.quantity} units of {brand} "
                f"at ₹{data.offered_price:.2f}/unit. Expiry: {inv.expiry_date.isoformat()}."
            ),
            severity=NotificationSeverity.INFO,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="transfer_request",
            resource_id=transfer.id,
        )

    db.commit()
    db.refresh(transfer)

    # Build response
    resp = OfferResponse.model_validate(transfer)
    resp.priority = transfer.priority.value
    resp.status = transfer.status.value
    resp.from_shop_name = from_shop.name
    resp.to_shop_name = to_shop.name
    resp.medicine_name = med.brand_name if med else None
    resp.salt_name = med.salt.formula_name if med and med.salt else None
    return resp


# ── GET /marketplace/offers — List marketplace offers ──────────

@router.get(
    "/offers",
    response_model=OfferListResponse,
    summary="List marketplace offers",
)
def list_offers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: TransferStatus | None = Query(None, alias="status"),
    from_shop_id: int | None = Query(None, description="Filter by source shop"),
    to_shop_id: int | None = Query(None, description="Filter by destination shop"),
):
    """List all marketplace offers (transfer requests with reason containing 'Marketplace')."""
    query = select(StockTransferRequest).where(
        StockTransferRequest.reason.like(f"%{MARKETPLACE_REASON_PREFIX}%")
    )

    if status_filter is not None:
        query = query.where(StockTransferRequest.status == status_filter)
    if from_shop_id is not None:
        query = query.where(StockTransferRequest.from_shop_id == from_shop_id)
    if to_shop_id is not None:
        query = query.where(StockTransferRequest.to_shop_id == to_shop_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    transfers = db.execute(
        query.order_by(StockTransferRequest.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()

    items = []
    for t in transfers:
        resp = OfferResponse.model_validate(t)
        resp.priority = t.priority.value
        resp.status = t.status.value
        if t.from_shop:
            resp.from_shop_name = t.from_shop.name
        if t.to_shop:
            resp.to_shop_name = t.to_shop.name
        med = db.execute(
            select(Medicine).where(Medicine.id == t.med_id)
        ).scalar_one_or_none()
        if med:
            resp.medicine_name = med.brand_name
            if med.salt:
                resp.salt_name = med.salt.formula_name
        items.append(resp)

    return OfferListResponse(items=items, total=total, page=page, size=size)


# ── PUT /marketplace/offers/{id}/accept ────────────────────────

@router.put(
    "/offers/{offer_id}/accept",
    response_model=OfferResponse,
    summary="Accept a marketplace offer",
)
def accept_offer(
    offer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Buyer accepts a marketplace offer. Sets status to APPROVED."""
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == offer_id)
    ).scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace offer with id={offer_id} not found",
        )

    if transfer.status != TransferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept offer in '{transfer.status.value}' status. Only PENDING offers can be accepted.",
        )

    if not transfer.reason or MARKETPLACE_REASON_PREFIX not in transfer.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a marketplace offer",
        )

    transfer.status = TransferStatus.APPROVED
    transfer.approved_by = current_user.id
    transfer.approved_at = datetime.now(timezone.utc)

    # Notify seller
    seller_users = _get_shop_users(db, transfer.from_shop_id)
    med = db.execute(
        select(Medicine).where(Medicine.id == transfer.med_id)
    ).scalar_one_or_none()
    brand = med.brand_name if med else "Unknown"
    for user in seller_users:
        _create_notification(
            db=db,
            user_id=user.id,
            title=f"Marketplace Offer Accepted: {brand}",
            message=(
                f"Your marketplace offer for {brand} ({transfer.quantity_requested} units) "
                f"has been accepted. Please arrange the transfer."
            ),
            severity=NotificationSeverity.INFO,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="transfer_request",
            resource_id=transfer.id,
        )

    db.commit()
    db.refresh(transfer)

    resp = OfferResponse.model_validate(transfer)
    resp.priority = transfer.priority.value
    resp.status = transfer.status.value
    if transfer.from_shop:
        resp.from_shop_name = transfer.from_shop.name
    if transfer.to_shop:
        resp.to_shop_name = transfer.to_shop.name
    resp.medicine_name = brand
    if med and med.salt:
        resp.salt_name = med.salt.formula_name
    return resp


# ── PUT /marketplace/offers/{id}/reject ────────────────────────

@router.put(
    "/offers/{offer_id}/reject",
    response_model=OfferResponse,
    summary="Reject a marketplace offer",
)
def reject_offer(
    offer_id: int,
    data: RejectOfferRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Buyer rejects a marketplace offer. Un-reserves inventory and notifies seller."""
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == offer_id)
    ).scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace offer with id={offer_id} not found",
        )

    if transfer.status != TransferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject offer in '{transfer.status.value}' status. Only PENDING offers can be rejected.",
        )

    if not transfer.reason or MARKETPLACE_REASON_PREFIX not in transfer.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a marketplace offer",
        )

    transfer.status = TransferStatus.REJECTED
    if transfer.reason:
        transfer.reason = f"{transfer.reason} [REJECTED: {data.reason}]"

    # Un-reserve the inventory
    if transfer.inventory_id:
        inv = db.execute(
            select(Inventory).where(Inventory.id == transfer.inventory_id)
        ).scalar_one_or_none()
        if inv:
            inv.is_reserved = False

    # Notify seller
    seller_users = _get_shop_users(db, transfer.from_shop_id)
    med = db.execute(
        select(Medicine).where(Medicine.id == transfer.med_id)
    ).scalar_one_or_none()
    brand = med.brand_name if med else "Unknown"
    for user in seller_users:
        _create_notification(
            db=db,
            user_id=user.id,
            title=f"Marketplace Offer Rejected: {brand}",
            message=(
                f"Your marketplace offer for {brand} ({transfer.quantity_requested} units) "
                f"has been rejected. Reason: {data.reason}"
            ),
            severity=NotificationSeverity.WARNING,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="transfer_request",
            resource_id=transfer.id,
        )

    db.commit()
    db.refresh(transfer)

    resp = OfferResponse.model_validate(transfer)
    resp.priority = transfer.priority.value
    resp.status = transfer.status.value
    if transfer.from_shop:
        resp.from_shop_name = transfer.from_shop.name
    if transfer.to_shop:
        resp.to_shop_name = transfer.to_shop.name
    resp.medicine_name = brand
    if med and med.salt:
        resp.salt_name = med.salt.formula_name
    return resp


# ── PUT /marketplace/offers/{id}/complete ──────────────────────

@router.put(
    "/offers/{offer_id}/complete",
    response_model=OfferResponse,
    summary="Complete a marketplace transfer",
)
def complete_offer(
    offer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
):
    """
    Mark a marketplace transfer as completed.
    Executes the transfer (decrement source, increment destination),
    creates audit logs and notifications for both shops. Admin only.
    """
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == offer_id)
    ).scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketplace offer with id={offer_id} not found",
        )

    if transfer.status != TransferStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete offer in '{transfer.status.value}' status. Only APPROVED offers can be completed.",
        )

    if not transfer.reason or MARKETPLACE_REASON_PREFIX not in transfer.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a marketplace offer",
        )

    # Step 1: Decrement source inventory
    if transfer.inventory_id:
        source_inv = db.execute(
            select(Inventory).where(Inventory.id == transfer.inventory_id)
        ).scalar_one_or_none()

        if source_inv and source_inv.quantity >= transfer.quantity_requested:
            old_src_qty = source_inv.quantity
            source_inv.quantity -= transfer.quantity_requested
            source_inv.is_reserved = False

            # Audit: source decremented
            _create_audit_log(
                db=db,
                action_type=ActionType.STOCK_ADJUSTED,
                user_id=current_user.id,
                description=(
                    f"Marketplace transfer out: {transfer.quantity_requested} units "
                    f"from shop {transfer.from_shop_id} (inventory #{source_inv.id})"
                ),
                details={
                    "source": "marketplace_complete",
                    "transfer_id": transfer.id,
                    "inventory_id": source_inv.id,
                    "old_quantity": old_src_qty,
                    "new_quantity": source_inv.quantity,
                    "adjustment": -transfer.quantity_requested,
                },
                resource_type="inventory",
                resource_id=source_inv.id,
                client_info=client_info,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source inventory has insufficient quantity for the transfer",
            )

    # Step 2: Increment destination inventory
    # Try to find existing inventory at destination with same med_id
    dest_inv = db.execute(
        select(Inventory)
        .where(
            Inventory.shop_id == transfer.to_shop_id,
            Inventory.med_id == transfer.med_id,
            Inventory.is_reserved == False,
        )
        .order_by(Inventory.expiry_date.asc())
        .limit(1)
    ).scalar_one_or_none()

    if dest_inv:
        old_dest_qty = dest_inv.quantity
        dest_inv.quantity += transfer.quantity_requested
        dest_inventory_id = dest_inv.id

        _create_audit_log(
            db=db,
            action_type=ActionType.STOCK_ADJUSTED,
            user_id=current_user.id,
            description=(
                f"Marketplace transfer in: {transfer.quantity_requested} units "
                f"to shop {transfer.to_shop_id} (inventory #{dest_inv.id})"
            ),
            details={
                "source": "marketplace_complete",
                "transfer_id": transfer.id,
                "inventory_id": dest_inv.id,
                "old_quantity": old_dest_qty,
                "new_quantity": dest_inv.quantity,
                "adjustment": transfer.quantity_requested,
            },
            resource_type="inventory",
            resource_id=dest_inv.id,
            client_info=client_info,
        )
    else:
        # Create new inventory record at destination
        source_inv_for_meta = None
        if transfer.inventory_id:
            source_inv_for_meta = db.execute(
                select(Inventory).where(Inventory.id == transfer.inventory_id)
            ).scalar_one_or_none()

        new_dest_inv = Inventory(
            med_id=transfer.med_id,
            shop_id=transfer.to_shop_id,
            quantity=transfer.quantity_requested,
            batch_number=source_inv_for_meta.batch_number if source_inv_for_meta else None,
            expiry_date=source_inv_for_meta.expiry_date if source_inv_for_meta else date.today(),
            cost_price=source_inv_for_meta.cost_price if source_inv_for_meta else None,
            selling_price=source_inv_for_meta.selling_price if source_inv_for_meta else None,
        )
        db.add(new_dest_inv)
        db.flush()
        dest_inventory_id = new_dest_inv.id

        _create_audit_log(
            db=db,
            action_type=ActionType.STOCK_ADDED,
            user_id=current_user.id,
            description=(
                f"Marketplace transfer in (new): {transfer.quantity_requested} units "
                f"to shop {transfer.to_shop_id}"
            ),
            details={
                "source": "marketplace_complete",
                "transfer_id": transfer.id,
                "inventory_id": dest_inventory_id,
                "quantity": transfer.quantity_requested,
            },
            resource_type="inventory",
            resource_id=dest_inventory_id,
            client_info=client_info,
        )

    # Step 3: Update transfer record
    transfer.status = TransferStatus.COMPLETED
    transfer.quantity_transferred = transfer.quantity_requested
    transfer.completed_at = datetime.now(timezone.utc)

    # Step 4: Create notifications for both shops
    med = db.execute(
        select(Medicine).where(Medicine.id == transfer.med_id)
    ).scalar_one_or_none()
    brand = med.brand_name if med else "Unknown"

    # Notify source shop
    source_users = _get_shop_users(db, transfer.from_shop_id)
    for user in source_users:
        _create_notification(
            db=db,
            user_id=user.id,
            title=f"Marketplace Transfer Completed: {brand}",
            message=(
                f"Your marketplace transfer of {brand} ({transfer.quantity_requested} units) "
                f"has been completed successfully."
            ),
            severity=NotificationSeverity.INFO,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="transfer_request",
            resource_id=transfer.id,
        )

    # Notify destination shop
    dest_users = _get_shop_users(db, transfer.to_shop_id)
    for user in dest_users:
        _create_notification(
            db=db,
            user_id=user.id,
            title=f"Marketplace Transfer Received: {brand}",
            message=(
                f"You have received {transfer.quantity_requested} units of {brand} "
                f"via marketplace transfer."
            ),
            severity=NotificationSeverity.INFO,
            source=NotificationSource.REDISTRIBUTION,
            resource_type="transfer_request",
            resource_id=transfer.id,
        )

    db.commit()
    db.refresh(transfer)

    resp = OfferResponse.model_validate(transfer)
    resp.priority = transfer.priority.value
    resp.status = transfer.status.value
    if transfer.from_shop:
        resp.from_shop_name = transfer.from_shop.name
    if transfer.to_shop:
        resp.to_shop_name = transfer.to_shop.name
    resp.medicine_name = brand
    if med and med.salt:
        resp.salt_name = med.salt.formula_name
    return resp


# ── GET /marketplace/dashboard ─────────────────────────────────

@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Marketplace dashboard summary",
)
def marketplace_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a comprehensive marketplace summary for the dashboard."""
    # Count expiring items
    expiring_items = _get_expiring_items(db, days=60)

    # Count demand matches (reuse logic)
    demand_matches_data = get_demand_matches.__wrapped__(db, current_user)

    # Count offers by status
    all_offers = db.execute(
        select(StockTransferRequest).where(
            StockTransferRequest.reason.like(f"%{MARKETPLACE_REASON_PREFIX}%")
        )
    ).scalars().all()

    offers_by_status: dict[str, int] = {
        "pending": 0,
        "approved": 0,
        "completed": 0,
        "rejected": 0,
    }
    shop_activity: dict[str, dict] = {}

    for t in all_offers:
        status_val = t.status.value
        if status_val in offers_by_status:
            offers_by_status[status_val] += 1

        # Track shop activity
        from_name = t.from_shop.name if t.from_shop else "Unknown"
        to_name = t.to_shop.name if t.to_shop else "Unknown"

        if from_name not in shop_activity:
            shop_activity[from_name] = {"listed": 0, "received": 0}
        shop_activity[from_name]["listed"] += 1

        if to_name not in shop_activity:
            shop_activity[to_name] = {"listed": 0, "received": 0}
        shop_activity[to_name]["received"] += 1

    # Top 10 most urgent expiring items
    top_expiring = []
    for item in expiring_items[:10]:
        med = item["medicine"]
        shop = item["shop"]
        salt_name = None
        if med and med.salt:
            salt_name = med.salt.formula_name
        top_expiring.append(TopExpiringItem(
            medicine_name=med.brand_name if med else "Unknown",
            salt_name=salt_name,
            shop_name=shop.name if shop else "Unknown",
            days_until_expiry=item["days_until_expiry"],
            quantity=item["inventory"].quantity,
            suggested_discount_pct=item["suggested_discount_pct"],
        ))

    return DashboardResponse(
        total_expiring_items=len(expiring_items),
        total_demand_matches=len(demand_matches_data),
        offers_by_status=offers_by_status,
        top_expiring_medicines=top_expiring,
        shop_activity=shop_activity,
    )


# ── GET /marketplace/shop/{shop_id}/listings ───────────────────

@router.get(
    "/shop/{shop_id}/listings",
    response_model=list[ExpiringListingItem],
    summary="Get shop's marketplace listings",
)
def shop_listings(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get this shop's marketplace listings (items they can sell, expiring within 60 days)."""
    today = date.today()
    cutoff = today + timedelta(days=60)

    # Validate shop
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found or inactive",
        )

    items = db.execute(
        select(Inventory)
        .where(
            Inventory.shop_id == shop_id,
            Inventory.expiry_date <= cutoff,
            Inventory.quantity > 0,
            Inventory.is_reserved == False,
        )
        .order_by(Inventory.expiry_date.asc())
    ).scalars().all()

    results = []
    for inv in items:
        delta = (inv.expiry_date - today).days
        med = inv.medicine
        salt_name = None
        if med and med.salt:
            salt_name = med.salt.formula_name

        results.append(ExpiringListingItem(
            inventory_id=inv.id,
            shop_name=shop.name,
            shop_id=shop_id,
            medicine_name=med.brand_name if med else "Unknown",
            salt_name=salt_name,
            quantity=inv.quantity,
            expiry_date=inv.expiry_date,
            days_until_expiry=delta,
            unit_price=inv.selling_price,
            suggested_discount_pct=_compute_suggested_discount(inv.expiry_date),
        ))

    return results


# ── GET /marketplace/shop/{shop_id}/opportunities ──────────────

@router.get(
    "/shop/{shop_id}/opportunities",
    response_model=list[DemandMatchItem],
    summary="Get buying opportunities for a shop",
)
def shop_opportunities(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get items this shop can buy (demand matches filtered for this shop)."""
    # Validate shop
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found or inactive",
        )

    # Get all demand matches and filter for this shop
    all_matches = get_demand_matches.__wrapped__(db, current_user)

    # Filter: only matches where dest_shop_id matches
    return [m for m in all_matches if m.dest_shop_id == shop_id]
