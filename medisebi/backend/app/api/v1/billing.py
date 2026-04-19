"""
MediSebi — Billing API Routes
==============================
REST endpoints for pharmacy billing, invoicing, and revenue tracking.
"""
from datetime import datetime, date, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, extract
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.bill import Bill, BillItem, PaymentMethod, BillStatus
from app.models.audit_log import AuditLog, ActionType
from app.core.audit_hash import compute_audit_hash
from app.core.config import settings
from app.schemas.billing import BillCreate, BillResponse, BillItemResponse, BillListResponse


router = APIRouter()


def _generate_invoice_number(db: Session, shop_id: int) -> str:
    """Generate invoice number: MED-YYYYMMDD-XXXX"""
    today = date.today().strftime("%Y%m%d")
    prefix = f"MED-{today}-"

    # Count bills created today for this shop
    count = db.execute(
        select(func.count()).select_from(Bill).where(
            Bill.invoice_number.like(f"{prefix}%")
        )
    ).scalar() or 0

    return f"{prefix}{count + 1:04d}"


def _calculate_gst_rate(selling_price: float) -> float:
    """Determine GST rate based on medicine price (Indian pharma GST slabs)."""
    if selling_price <= 100:
        return 5.0  # Nil/5% for cheap medicines
    elif selling_price <= 500:
        return 12.0
    else:
        return 18.0


def _create_audit_entry(db: Session, user_id: int, action: str, details: dict):
    """Create an audit log entry."""
    detail_str = str(details)
    audit = AuditLog(
        user_id=user_id,
        action_type=action,
        entity_type="bill",
        entity_id=0,  # Will be updated after bill creation
        details=detail_str,
        ip_address="system",
        hash_value=compute_audit_hash(detail_str),
    )
    db.add(audit)


# ── CREATE BILL ─────────────────────────────────────────────
@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    body: BillCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Create a new bill (invoice) and deduct stock from inventory."""

    # Validate shop
    shop = db.execute(select(Shop).where(Shop.id == body.shop_id)).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {body.shop_id} not found")

    # Validate payment method
    try:
        PaymentMethod(body.payment_method.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment method: {body.payment_method}")

    # Validate items and collect inventory data
    item_data = []
    total_gst = 0.0

    for item in body.items:
        inv = db.execute(
            select(Inventory).where(Inventory.id == item.inventory_id)
        ).scalar_one_or_none()

        if not inv:
            raise HTTPException(status_code=404, detail=f"Inventory item {item.inventory_id} not found")

        if inv.shop_id != body.shop_id:
            raise HTTPException(status_code=400, detail=f"Inventory item {item.inventory_id} does not belong to shop {body.shop_id}")

        if inv.quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {inv.medicine.brand_name if inv.medicine else 'item'}: available={inv.quantity}, requested={item.quantity}")

        if inv.is_reserved:
            raise HTTPException(status_code=400, detail=f"Inventory item {item.inventory_id} is reserved and cannot be sold")

        med = inv.medicine
        unit_price = inv.selling_price or 0.0
        gst_rate = _calculate_gst_rate(unit_price)

        item_total_before_discount = item.quantity * unit_price
        item_total = max(0, item_total_before_discount - item.discount)
        gst_amount = item_total * gst_rate / 100

        item_data.append({
            "inventory": inv,
            "medicine": med,
            "unit_price": unit_price,
            "cost_price": inv.cost_price,
            "gst_rate": gst_rate,
            "item_total_before_discount": item_total_before_discount,
            "item_total": item_total,
            "gst_amount": gst_amount,
            "quantity": item.quantity,
            "discount": item.discount,
        })
        total_gst += gst_amount

    # Calculate totals
    subtotal = sum(d["item_total_before_discount"] for d in item_data)
    total_item_discount = sum(d["discount"] for d in item_data)

    if body.discount_percent:
        overall_discount = subtotal * body.discount_percent / 100
    else:
        overall_discount = total_item_discount

    taxable_amount = subtotal - overall_discount
    cgst = taxable_amount * 0.025  # 2.5% CGST
    sgst = taxable_amount * 0.025  # 2.5% SGST
    total_amount = taxable_amount + cgst + sgst

    # Create bill
    bill = Bill(
        invoice_number=_generate_invoice_number(db, body.shop_id),
        shop_id=body.shop_id,
        created_by=current_user.id,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        doctor_name=body.doctor_name,
        subtotal=subtotal,
        discount_amount=overall_discount,
        discount_percent=body.discount_percent,
        cgst_amount=round(cgst, 2),
        sgst_amount=round(sgst, 2),
        total_amount=round(total_amount, 2),
        amount_paid=round(total_amount, 2),
        status=BillStatus.PAID.value,
        payment_method=body.payment_method.lower(),
        notes=body.notes,
    )
    db.add(bill)
    db.flush()  # Get the bill ID

    # Create bill items and deduct inventory
    for d in item_data:
        inv = d["inventory"]
        med = d["medicine"]

        bill_item = BillItem(
            bill_id=bill.id,
            inventory_id=inv.id,
            med_id=med.id,
            medicine_name=med.brand_name,
            salt_name=med.salt.salt_name if med.salt else None,
            batch_number=inv.batch_number,
            expiry_date=str(inv.expiry_date) if inv.expiry_date else None,
            quantity=d["quantity"],
            unit_price=d["unit_price"],
            cost_price=d["cost_price"],
            item_total=round(d["item_total"], 2),
            discount=d["discount"],
            gst_rate=d["gst_rate"],
            gst_amount=round(d["gst_amount"], 2),
        )
        db.add(bill_item)

        # Deduct inventory
        inv.quantity -= d["quantity"]
        # version_id is auto-incremented by SQLAlchemy optimistic locking

    # Create audit log
    audit = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.BILL_CREATED.value if hasattr(ActionType, 'BILL_CREATED') else "BILL_CREATED",
        entity_type="bill",
        entity_id=bill.id,
        details=f"Bill {bill.invoice_number}: ₹{bill.total_amount} with {len(item_data)} items at shop {shop.name}",
        ip_address="system",
        hash_value=compute_audit_hash(f"bill:{bill.id}"),
    )
    db.add(audit)

    db.commit()
    db.refresh(bill)

    return bill


# ── LIST BILLS ──────────────────────────────────────────────
@router.get("/", response_model=BillListResponse)
def list_bills(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    shop_id: Optional[int] = Query(None),
    customer_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List bills with filters and pagination."""
    stmt = select(Bill).order_by(Bill.created_at.desc())

    if shop_id:
        stmt = stmt.where(Bill.shop_id == shop_id)
    if customer_name:
        stmt = stmt.where(Bill.customer_name.ilike(f"%{customer_name}%"))
    if status:
        stmt = stmt.where(Bill.status == status.lower())
    if from_date:
        stmt = stmt.where(Bill.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        stmt = stmt.where(Bill.created_at <= datetime.combine(to_date, datetime.max.time()))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    bills = db.execute(stmt.offset((page - 1) * size).limit(size)).scalars().all()

    return BillListResponse(
        items=bills,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total > 0 else 1,
    )


# ── GET BILL DETAIL ────────────────────────────────────────
@router.get("/{bill_id}", response_model=BillResponse)
def get_bill(
    bill_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get full bill details with all line items."""
    bill = db.execute(
        select(Bill).where(Bill.id == bill_id)
    ).scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id} not found")

    return bill


# ── TODAY'S BILLS ──────────────────────────────────────────
@router.get("/shop/{shop_id}/today")
def today_bills(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Get today's bills for a shop with summary."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    stmt = select(Bill).where(
        and_(Bill.shop_id == shop_id, Bill.created_at >= today_start, Bill.created_at <= today_end)
    ).order_by(Bill.created_at.desc())

    bills = db.execute(stmt).scalars().all()

    summary = db.execute(
        select(
            func.count(Bill.id),
            func.sum(Bill.total_amount),
            func.avg(Bill.total_amount),
        ).where(
            and_(Bill.shop_id == shop_id, Bill.created_at >= today_start, Bill.created_at <= today_end, Bill.status == "paid")
        )
    ).one()

    return {
        "date": date.today().isoformat(),
        "total_bills": summary[0] or 0,
        "total_revenue": float(summary[1] or 0),
        "avg_bill_amount": float(summary[2] or 0),
        "bills": [
            {
                "id": b.id,
                "invoice_number": b.invoice_number,
                "customer_name": b.customer_name,
                "total_amount": b.total_amount,
                "status": b.status,
                "payment_method": b.payment_method,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bills
        ],
    }


# ── REVENUE SUMMARY ────────────────────────────────────────
@router.get("/shop/{shop_id}/revenue")
def revenue_summary(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    period: Optional[str] = Query("month"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
):
    """Revenue summary for a shop."""
    # Determine date range
    today = date.today()
    if from_date and to_date:
        start_dt = datetime.combine(from_date, datetime.min.time())
        end_dt = datetime.combine(to_date, datetime.max.time())
    elif period == "today":
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
    elif period == "week":
        start_dt = datetime.combine(today - timedelta(days=7), datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
    elif period == "month":
        start_dt = datetime.combine(today.replace(day=1), datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
    elif period == "year":
        start_dt = datetime.combine(today.replace(month=1, day=1), datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
    else:
        start_dt = datetime.combine(today.replace(day=1), datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())

    base_filter = and_(
        Bill.shop_id == shop_id,
        Bill.created_at >= start_dt,
        Bill.created_at <= end_dt,
        Bill.status == "paid",
    )

    # Revenue stats
    stats = db.execute(
        select(
            func.count(Bill.id),
            func.sum(Bill.total_amount),
            func.avg(Bill.total_amount),
            func.sum(Bill.discount_amount),
            func.sum(Bill.cgst_amount),
            func.sum(Bill.sgst_amount),
            func.sum(Bill.amount_paid),
        ).where(base_filter)
    ).one()

    # Payment method breakdown
    payment_breakdown = db.execute(
        select(Bill.payment_method, func.count(Bill.id), func.sum(Bill.total_amount))
        .where(base_filter)
        .group_by(Bill.payment_method)
    ).all()

    return {
        "period": period,
        "from_date": start_dt.isoformat(),
        "to_date": end_dt.isoformat(),
        "total_bills": stats[0] or 0,
        "total_revenue": float(stats[1] or 0),
        "avg_bill_amount": float(stats[2] or 0),
        "total_discount": float(stats[3] or 0),
        "total_cgst": float(stats[4] or 0),
        "total_sgst": float(stats[5] or 0),
        "total_gst": float((stats[4] or 0) + (stats[5] or 0)),
        "total_collected": float(stats[6] or 0),
        "payment_method_breakdown": [
            {"method": pm, "count": cnt, "revenue": float(rev or 0)}
            for pm, cnt, rev in payment_breakdown
        ],
    }


# ── CANCEL BILL ─────────────────────────────────────────────
@router.put("/{bill_id}/cancel", response_model=BillResponse)
def cancel_bill(
    bill_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """Cancel a bill and restore inventory quantities."""
    bill = db.execute(
        select(Bill).options(joinedload(Bill.items)).where(Bill.id == bill_id)
    ).scalar_one_or_none()

    if not bill:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id} not found")

    if bill.status == BillStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Bill is already cancelled")

    if bill.status == BillStatus.REFUNDED.value:
        raise HTTPException(status_code=400, detail="Cannot cancel a refunded bill")

    # Restore inventory
    for item in bill.items:
        inv = db.execute(select(Inventory).where(Inventory.id == item.inventory_id)).scalar_one_or_none()
        if inv:
            inv.quantity += item.quantity

    bill.status = BillStatus.CANCELLED.value

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action_type="BILL_CANCELLED",
        entity_type="bill",
        entity_id=bill.id,
        details=f"Bill {bill.invoice_number} cancelled by {current_user.full_name}. Restored {len(bill.items)} items.",
        ip_address="system",
        hash_value=compute_audit_hash(f"cancel:{bill.id}"),
    )
    db.add(audit)

    db.commit()
    db.refresh(bill)

    return bill
