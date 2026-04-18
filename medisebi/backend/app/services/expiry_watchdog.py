"""
MediSebi — Expiry Watchdog Service
====================================
Scans inventory for items approaching or past their expiry date.
Categorises items by urgency (EXPIRED / URGENT / WARNING) and creates
Notification records for newly detected expiring items (deduplicated).

Configured thresholds:
    - EXPIRED  : expiry_date < today          → CRITICAL
    - URGENT   : expiry_date < today + 7 days → CRITICAL
    - WARNING  : expiry_date < today + 30 days → WARNING
"""

from datetime import date, timedelta, datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.shop import Shop
from app.models.notification import Notification, NotificationSeverity, NotificationSource


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _categorise(expiry: date, today: date) -> tuple[str, NotificationSeverity]:
    """Return (category, severity) for an inventory expiry date."""
    if expiry < today:
        return "EXPIRED", NotificationSeverity.CRITICAL
    elif expiry < today + timedelta(days=7):
        return "URGENT", NotificationSeverity.CRITICAL
    else:
        return "WARNING", NotificationSeverity.WARNING


def _is_already_notified(db: Session, inventory_id: int) -> bool:
    """Check whether a notification already exists for this inventory item."""
    stmt = select(func.count()).select_from(Notification).where(
        and_(
            Notification.resource_type == "inventory",
            Notification.resource_id == inventory_id,
            Notification.source == NotificationSource.EXPIRY_WATCHDOG,
        )
    )
    count = db.execute(stmt).scalar() or 0
    return count > 0


def _create_notification(
    db: Session,
    shop_id: int,
    inventory_id: int,
    brand_name: str,
    category: str,
    expiry: date,
    severity: NotificationSeverity,
) -> None:
    """Create a notification for every staff member assigned to the shop."""
    # Find all staff assigned to this shop
    from app.models.shop_staff import ShopStaff
    from app.models.user import User

    staff_stmt = select(ShopStaff.user_id).where(ShopStaff.shop_id == shop_id)
    user_ids = [row[0] for row in db.execute(staff_stmt).all()]

    if not user_ids:
        # No staff assigned — skip notification (or could notify admins)
        return

    days_left = (expiry - date.today()).days
    if category == "EXPIRED":
        title = f"EXPIRED: {brand_name}"
        message = (
            f"{brand_name} has EXPIRED (was due {expiry}). "
            "Remove from shelves immediately. "
            f"Inventory ID: {inventory_id}"
        )
    else:
        title = f"{category}: {brand_name} expires in {days_left}d"
        message = (
            f"{brand_name} expires on {expiry} ({days_left} days remaining). "
            f"Category: {category}. Inventory ID: {inventory_id}"
        )

    for uid in user_ids:
        notif = Notification(
            user_id=uid,
            title=title,
            message=message,
            severity=severity,
            source=NotificationSource.EXPIRY_WATCHDOG,
            resource_type="inventory",
            resource_id=inventory_id,
            action_url=f"/inventory/{inventory_id}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.NOTIFICATION_CRITICAL_TTL_DAYS),
        )
        db.add(notif)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_expiry_alerts(db: Session) -> list[dict]:
    """
    Scan all inventory items expiring within EXPIRY_WARNING_DAYS.

    Returns a list of dicts, one per shop, with severity breakdowns:

        {
            "shop_id": 1,
            "shop_name": "Mumbai Central Pharmacy",
            "expired": 3,
            "urgent": 2,
            "warning": 5,
            "items": [ ... detailed item list ... ]
        }
    """
    today = date.today()
    cutoff = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    # Join inventory → medicine → salt to get full picture
    stmt = (
        select(Inventory, Medicine, Salt, Shop)
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .join(Shop, Inventory.shop_id == Shop.id)
        .where(Inventory.expiry_date <= cutoff)
        .order_by(Inventory.expiry_date.asc())
    )

    rows = db.execute(stmt).all()

    # Group results by shop
    shop_map: dict[int, dict] = {}
    for inv, med, salt, shop in rows:
        category, severity = _categorise(inv.expiry_date, today)

        if shop.id not in shop_map:
            shop_map[shop.id] = {
                "shop_id": shop.id,
                "shop_name": shop.name,
                "shop_code": shop.code,
                "city": shop.city,
                "expired": 0,
                "urgent": 0,
                "warning": 0,
                "items": [],
            }

        bucket = shop_map[shop.id]
        if category == "EXPIRED":
            bucket["expired"] += 1
        elif category == "URGENT":
            bucket["urgent"] += 1
        else:
            bucket["warning"] += 1

        bucket["items"].append({
            "inventory_id": inv.id,
            "medicine_id": med.id,
            "brand_name": med.brand_name,
            "salt_name": salt.formula_name,
            "salt_category": salt.category,
            "quantity": inv.quantity,
            "expiry_date": inv.expiry_date.isoformat(),
            "category": category,
            "severity": severity.value,
        })

        # Create notification if this is a newly detected item
        if not _is_already_notified(db, inv.id):
            _create_notification(
                db=db,
                shop_id=shop.id,
                inventory_id=inv.id,
                brand_name=med.brand_name,
                category=category,
                expiry=inv.expiry_date,
                severity=severity,
            )

    db.flush()
    return list(shop_map.values())


def get_expiry_summary(db: Session) -> dict:
    """
    Return aggregate counts for the expiry dashboard.

    Top-level counts plus breakdowns by shop and by salt category.
    """
    today = date.today()
    warning_cutoff = today + timedelta(days=settings.EXPIRY_WARNING_DAYS)

    # Base query: all items within the warning window
    base = (
        select(
            Inventory.id,
            Inventory.shop_id,
            Inventory.expiry_date,
            Inventory.quantity,
            Medicine.brand_name,
            Medicine.id.label("med_id"),
            Salt.id.label("salt_id"),
            Salt.formula_name,
            Salt.category,
            Shop.name.label("shop_name"),
        )
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .join(Shop, Inventory.shop_id == Shop.id)
        .where(Inventory.expiry_date <= warning_cutoff)
    )

    rows = db.execute(base).all()

    # Total items in the system (for safe count)
    total_items = db.execute(select(func.count()).select_from(Inventory)).scalar() or 0

    expired_count = 0
    urgent_count = 0
    warning_count = 0

    by_shop: dict[int, dict] = {}
    by_category: dict[str, dict] = {}

    for row in rows:
        expiry = row.expiry_date
        category, _ = _categorise(expiry, today)

        if category == "EXPIRED":
            expired_count += 1
        elif category == "URGENT":
            urgent_count += 1
        else:
            warning_count += 1

        # By shop
        sid = row.shop_id
        if sid not in by_shop:
            by_shop[sid] = {
                "shop_id": sid,
                "shop_name": row.shop_name,
                "expired": 0,
                "urgent": 0,
                "warning": 0,
            }
        if category == "EXPIRED":
            by_shop[sid]["expired"] += 1
        elif category == "URGENT":
            by_shop[sid]["urgent"] += 1
        else:
            by_shop[sid]["warning"] += 1

        # By salt category
        cat = row.category or "Unknown"
        if cat not in by_category:
            by_category[cat] = {
                "category": cat,
                "expired": 0,
                "urgent": 0,
                "warning": 0,
            }
        if category == "EXPIRED":
            by_category[cat]["expired"] += 1
        elif category == "URGENT":
            by_category[cat]["urgent"] += 1
        else:
            by_category[cat]["warning"] += 1

    safe_count = total_items - expired_count - urgent_count - warning_count

    return {
        "total_items": total_items,
        "expired_count": expired_count,
        "urgent_count": urgent_count,
        "warning_count": warning_count,
        "safe_count": safe_count,
        "by_shop": list(by_shop.values()),
        "by_category": list(by_category.values()),
    }
