"""
MediSebi — Transfer / Redistribution API Router
=================================================
REST endpoints for the Smart Redistribution Engine (Tier 3).
Handles transfer request creation, approval, execution, rejection,
and redistribution analysis across the pharmacy network.

Endpoints:
    GET  /transfers/analyze              — Run redistribution analysis
    GET  /transfers/analyze/shop/{id}    — Shop-specific analysis
    POST /transfers/request              — Create a transfer request
    GET  /transfers                      — List transfer requests
    GET  /transfers/{id}                 — Get transfer details
    PUT  /transfers/{id}/approve         — Approve a transfer (admin)
    PUT  /transfers/{id}/execute         — Execute a transfer (admin)
    PUT  /transfers/{id}/reject          — Reject a transfer (admin)
    GET  /transfers/analytics            — Dashboard analytics
    GET  /transfers/shop/{id}/history    — Shop transfer history
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.auth.dependencies import (
    get_current_user,
    get_client_info,
    require_role,
)
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.medicine import Medicine
from app.models.stock_transfer import (
    StockTransferRequest,
    TransferStatus,
    TransferPriority,
)
from app.services.redistribution_engine import (
    analyze_redistribution_opportunities,
    analyze_shop_redistribution,
    create_transfer_request,
    approve_transfer_request,
    execute_transfer,
    reject_transfer_request,
    get_transfer_analytics,
    get_shop_transfer_history,
)

router = APIRouter(tags=["Redistribution"])


# ── Pydantic Schemas ───────────────────────────────────────────

class TransferRequestCreate(BaseModel):
    """Schema for creating a manual transfer request."""
    from_shop_id: int = Field(..., description="Source shop ID (excess stock)")
    to_shop_id: int = Field(..., description="Destination shop ID (deficit)")
    med_id: int = Field(..., description="Medicine ID to transfer")
    quantity: int = Field(..., gt=0, description="Number of units to transfer")
    priority: TransferPriority = Field(
        default=TransferPriority.MEDIUM,
        description="Transfer urgency level",
    )
    reason: str = Field(..., min_length=5, description="Reason for the transfer")
    inventory_id: int | None = Field(None, description="Specific inventory batch ID (optional)")


class TransferRejectRequest(BaseModel):
    """Schema for rejecting a transfer request."""
    reason: str = Field(..., min_length=3, description="Reason for rejection")


class TransferResponse(BaseModel):
    """Schema for a transfer request response."""
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
    # Enriched fields
    from_shop_name: str | None = None
    to_shop_name: str | None = None
    medicine_name: str | None = None
    salt_name: str | None = None

    model_config = {"from_attributes": True}


class TransferListResponse(BaseModel):
    """Paginated list of transfer requests."""
    items: list[TransferResponse]
    total: int
    page: int
    size: int


# ── Helper: Enrich transfer response ──────────────────────────

def _enrich_transfer(db: Session, transfer: StockTransferRequest) -> TransferResponse:
    """Enrich a transfer request with shop and medicine names."""
    resp = TransferResponse.model_validate(transfer)
    resp.priority = transfer.priority.value
    resp.status = transfer.status.value

    if transfer.from_shop:
        resp.from_shop_name = transfer.from_shop.name
    if transfer.to_shop:
        resp.to_shop_name = transfer.to_shop.name

    med = db.execute(
        select(Medicine).where(Medicine.id == transfer.med_id)
    ).scalar_one_or_none()
    if med:
        resp.medicine_name = med.brand_name
        if med.salt:
            resp.salt_name = med.salt.formula_name

    return resp


# ── ANALYZE: Global redistribution ────────────────────────────

@router.get(
    "/analyze",
    summary="Run redistribution analysis",
    description="Scan all shops and return transfer recommendations. Admin and Pharmacist roles.",
)
def analyze_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """
    Run the Smart Redistribution Engine analysis across all shops.
    Returns a prioritized list of transfer recommendations.
    """
    opportunities = analyze_redistribution_opportunities(db)
    return {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_opportunities": len(opportunities),
        "opportunities": opportunities,
    }


# ── ANALYZE: Shop-specific redistribution ─────────────────────

@router.get(
    "/analyze/shop/{shop_id}",
    summary="Analyze redistribution for a specific shop",
    description="Get redistribution opportunities for a specific shop (both incoming and outgoing).",
)
def analyze_for_shop(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """
    Analyze redistribution opportunities specific to a single shop.
    Returns both incoming (deficit) and outgoing (excess) opportunities.
    """
    # Validate shop exists
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found or inactive",
        )

    result = analyze_shop_redistribution(db, shop_id)
    result["shop_name"] = shop.name
    result["shop_code"] = shop.code
    return result


# ── CREATE: Manual transfer request ───────────────────────────

@router.post(
    "/request",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transfer request",
    description="Manually create a new stock transfer request. Admin/Pharmacist only.",
)
def create_transfer(
    data: TransferRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """
    Create a new transfer request manually.
    The request will be in PENDING status awaiting admin approval.
    """
    # Validate source shop
    from_shop = db.execute(
        select(Shop).where(Shop.id == data.from_shop_id, Shop.is_active == True)
    ).scalar_one_or_none()
    if not from_shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source shop with id={data.from_shop_id} not found or inactive",
        )

    # Validate destination shop
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
            detail="Source and destination shops cannot be the same",
        )

    # Validate medicine
    med = db.execute(
        select(Medicine).where(Medicine.id == data.med_id, Medicine.is_active == True)
    ).scalar_one_or_none()
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with id={data.med_id} not found or inactive",
        )

    # Validate inventory_id if provided
    if data.inventory_id:
        from app.models.inventory import Inventory
        inv = db.execute(
            select(Inventory).where(
                Inventory.id == data.inventory_id,
                Inventory.shop_id == data.from_shop_id,
                Inventory.med_id == data.med_id,
            )
        ).scalar_one_or_none()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory batch id={data.inventory_id} not found or doesn't match source shop/medicine",
            )
        if inv.quantity < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock in batch. Available: {inv.quantity}, Requested: {data.quantity}",
            )

    transfer = create_transfer_request(
        db=db,
        from_shop_id=data.from_shop_id,
        to_shop_id=data.to_shop_id,
        med_id=data.med_id,
        quantity=data.quantity,
        priority=data.priority,
        reason=data.reason,
        inventory_id=data.inventory_id,
        requested_by_user_id=current_user.id,
    )

    return _enrich_transfer(db, transfer)


# ── LIST: All transfer requests ───────────────────────────────

@router.get(
    "/",
    response_model=TransferListResponse,
    summary="List transfer requests",
    description="List all transfer requests with optional filters and pagination.",
)
def list_transfers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: TransferStatus | None = Query(None, alias="status"),
    from_shop_id: int | None = Query(None, description="Filter by source shop"),
    to_shop_id: int | None = Query(None, description="Filter by destination shop"),
    priority_filter: TransferPriority | None = Query(None, alias="priority"),
):
    """List all transfer requests with optional filters."""
    query = select(StockTransferRequest)

    if status_filter is not None:
        query = query.where(StockTransferRequest.status == status_filter)
    if from_shop_id is not None:
        query = query.where(StockTransferRequest.from_shop_id == from_shop_id)
    if to_shop_id is not None:
        query = query.where(StockTransferRequest.to_shop_id == to_shop_id)
    if priority_filter is not None:
        query = query.where(StockTransferRequest.priority == priority_filter)

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    transfers = db.execute(
        query.order_by(StockTransferRequest.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()

    items = [_enrich_transfer(db, t) for t in transfers]
    return TransferListResponse(items=items, total=total, page=page, size=size)


# ── ANALYTICS & HISTORY (MUST be before /{transfer_id}) ─────────

@router.get(
    "/analytics",
    summary="Get transfer analytics",
    description="Get analytics data for the transfer dashboard. Admin/Pharmacist.",
)
def transfer_analytics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Get transfer analytics for the dashboard."""
    return get_transfer_analytics(db)


@router.get(
    "/shop/{shop_id}/history",
    summary="Get shop transfer history",
    description="Get transfer history for a specific shop (both incoming and outgoing).",
)
def shop_history(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: TransferStatus | None = Query(None, alias="status"),
):
    """Get the transfer history for a specific shop."""
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found or inactive",
        )

    return get_shop_transfer_history(
        db=db,
        shop_id=shop_id,
        status_filter=status_filter,
        page=page,
        size=size,
    )


# ── GET: Single transfer request ──────────────────────────────

@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Get transfer request details",
    description="Get detailed information about a specific transfer request.",
)
def get_transfer(
    transfer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a single transfer request by ID."""
    transfer = db.execute(
        select(StockTransferRequest).where(StockTransferRequest.id == transfer_id)
    ).scalar_one_or_none()

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer request with id={transfer_id} not found",
        )

    return _enrich_transfer(db, transfer)


# ── APPROVE: Approve a transfer (admin only) ──────────────────

@router.put(
    "/{transfer_id}/approve",
    response_model=TransferResponse,
    summary="Approve a transfer request",
    description="Approve a pending transfer request. Admin only.",
)
def approve_transfer(
    transfer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """Approve a pending transfer request. Sets status to APPROVED."""
    try:
        transfer = approve_transfer_request(
            db=db,
            request_id=transfer_id,
            approved_by_user_id=current_user.id,
        )
        return _enrich_transfer(db, transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── EXECUTE: Execute an approved transfer (admin only) ────────

@router.put(
    "/{transfer_id}/execute",
    summary="Execute an approved transfer",
    description="Execute an approved transfer. Moves stock from source to destination. Admin only.",
)
def execute_transfer_endpoint(
    transfer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """
    Execute an approved transfer.
    Atomically decrements source inventory and increments destination inventory.
    Creates audit logs and notifications for both shops.
    """
    try:
        result = execute_transfer(
            db=db,
            request_id=transfer_id,
            executed_by_user_id=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── REJECT: Reject a transfer request (admin only) ────────────

@router.put(
    "/{transfer_id}/reject",
    response_model=TransferResponse,
    summary="Reject a transfer request",
    description="Reject a transfer request with reason. Admin only.",
)
def reject_transfer(
    transfer_id: int,
    data: TransferRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """Reject a transfer request with a reason."""
    try:
        transfer = reject_transfer_request(
            db=db,
            request_id=transfer_id,
            rejected_by_user_id=current_user.id,
            reason=data.reason,
        )
        return _enrich_transfer(db, transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )



