"""
MediSebi — Expiry Watchdog API Routes
========================================
REST endpoints for the Expiry Watchdog system.
Provides scan triggering, dashboard summaries, and filtered item listings.
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.shop import Shop
from app.services.expiry_watchdog import scan_expiry_alerts, get_expiry_summary, _categorise

router = APIRouter()


# ── MANUAL SCAN ──────────────────────────────────────────────────
@router.get("/scan", summary="Manually trigger expiry scan")
def trigger_expiry_scan(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    """
    Trigger an expiry scan across all inventory.
    Creates notifications for newly detected expiring items (deduplicated).
    Returns per-shop severity breakdown.
    """
    results = scan_expiry_alerts(db)
    db.commit()
    return {
        "status": "ok",
        "message": f"Expiry scan complete. Found alerts for {len(results)} shop(s).",
        "shops": results,
    }


# ── DASHBOARD SUMMARY ────────────────────────────────────────────
@router.get("/summary", summary="Get expiry dashboard summary")
def expiry_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Aggregate counts: total, expired, urgent, warning, safe.
    Broken down by shop and by salt category.
    """
    return get_expiry_summary(db)


# ── LIST EXPIRING ITEMS (paginated, filterable) ─────────────────
@router.get("/items", summary="List all expiring items")
def list_expiring_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    shop_id: int | None = Query(None, description="Filter by shop ID"),
    severity: str | None = Query(None, description="Filter: expired, urgent, warning"),
    salt_category: str | None = Query(None, description="Filter by salt category"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Paginated list of all inventory items expiring within the warning window.
    Supports filtering by shop, severity, and salt category.
    """
    today = date.today()
    cutoff = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    stmt = (
        select(
            Inventory.id,
            Inventory.shop_id,
            Inventory.quantity,
            Inventory.batch_number,
            Inventory.expiry_date,
            Inventory.cost_price,
            Inventory.selling_price,
            Medicine.id.label("medicine_id"),
            Medicine.brand_name,
            Salt.id.label("salt_id"),
            Salt.formula_name.label("salt_name"),
            Salt.category.label("salt_category"),
            Shop.name.label("shop_name"),
            Shop.city.label("shop_city"),
        )
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .join(Shop, Inventory.shop_id == Shop.id)
        .where(Inventory.expiry_date <= cutoff)
        .order_by(Inventory.expiry_date.asc())
    )

    # Apply filters
    if shop_id is not None:
        stmt = stmt.where(Inventory.shop_id == shop_id)

    if salt_category is not None:
        stmt = stmt.where(Salt.category == salt_category)

    # Severity filter — applied post-fetch since it's computed
    # We'll collect all rows first, then filter by severity in Python
    all_rows = db.execute(stmt).all()

    filtered = []
    for row in all_rows:
        category, sev = _categorise(row.expiry_date, today)
        if severity is not None and category.lower() != severity.lower():
            continue
        filtered.append({
            "inventory_id": row.id,
            "medicine_id": row.medicine_id,
            "brand_name": row.brand_name,
            "salt_id": row.salt_id,
            "salt_name": row.salt_name,
            "salt_category": row.salt_category,
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "shop_city": row.shop_city,
            "quantity": row.quantity,
            "batch_number": row.batch_number,
            "expiry_date": row.expiry_date.isoformat(),
            "cost_price": row.cost_price,
            "selling_price": row.selling_price,
            "category": category,
            "severity": sev.value,
        })

    total = len(filtered)
    start = (page - 1) * size
    paginated = filtered[start : start + size]

    return {
        "items": paginated,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 1,
    }


# ── SHOP-SPECIFIC STATUS ────────────────────────────────────────
@router.get("/shop/{shop_id}", summary="Get expiry status for a specific shop")
def shop_expiry_status(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Expiry status for a single shop: counts by severity + item list.
    """
    # Verify shop exists
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id)
    ).scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found",
        )

    today = date.today()
    cutoff = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    stmt = (
        select(
            Inventory.id,
            Inventory.quantity,
            Inventory.expiry_date,
            Medicine.brand_name,
            Salt.formula_name,
            Salt.category,
        )
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(
            and_(
                Inventory.shop_id == shop_id,
                Inventory.expiry_date <= cutoff,
            )
        )
        .order_by(Inventory.expiry_date.asc())
    )

    rows = db.execute(stmt).all()

    expired_items = []
    urgent_items = []
    warning_items = []

    for row in rows:
        cat, sev = _categorise(row.expiry_date, today)
        item = {
            "inventory_id": row.id,
            "brand_name": row.brand_name,
            "salt_name": row.formula_name,
            "salt_category": row.category,
            "quantity": row.quantity,
            "expiry_date": row.expiry_date.isoformat(),
            "category": cat,
            "severity": sev.value,
        }
        if cat == "EXPIRED":
            expired_items.append(item)
        elif cat == "URGENT":
            urgent_items.append(item)
        else:
            warning_items.append(item)

    return {
        "shop_id": shop_id,
        "shop_name": shop.name,
        "shop_code": shop.code,
        "city": shop.city,
        "expired_count": len(expired_items),
        "urgent_count": len(urgent_items),
        "warning_count": len(warning_items),
        "expired_items": expired_items,
        "urgent_items": urgent_items,
        "warning_items": warning_items,
    }


# ── BY-CATEGORY STATS (for charts) ──────────────────────────────
@router.get("/stats/by-category", summary="Expiring items by salt category")
def stats_by_category(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Breakdown of expiring items by salt category (suitable for charts).
    Returns counts per severity per category.
    """
    today = date.today()
    cutoff = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    stmt = (
        select(
            Salt.category,
            Inventory.id,
            Inventory.expiry_date,
        )
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(Inventory.expiry_date <= cutoff)
    )

    rows = db.execute(stmt).all()

    categories: dict[str, dict] = {}
    for row in rows:
        cat_name = row.category or "Unknown"
        if cat_name not in categories:
            categories[cat_name] = {
                "category": cat_name,
                "expired": 0,
                "urgent": 0,
                "warning": 0,
                "total": 0,
            }
        cat_label, _ = _categorise(row.expiry_date, today)
        categories[cat_name]["total"] += 1
        if cat_label == "EXPIRED":
            categories[cat_name]["expired"] += 1
        elif cat_label == "URGENT":
            categories[cat_name]["urgent"] += 1
        else:
            categories[cat_name]["warning"] += 1

    return {
        "categories": list(categories.values()),
    }
