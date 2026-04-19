"""
MediSebi — Medicine Catalog API
================================
Browse, search, and quickly add medicines from the master catalog
to shop inventory. Supports bulk-add and stock-check operations.

Endpoints:
    GET  /catalog                        — Browse full catalog with pagination, optional category filter
    GET  /catalog/search?q=paracetamol  — Search by name, salt, manufacturer, category
    GET  /catalog/categories           — List all categories with medicine count per category
    GET  /catalog/{index}               — Get a specific catalog item by its index
    POST /catalog/quick-add            — Add medicine from catalog to shop inventory
    POST /catalog/bulk-add             — Add multiple medicines from catalog at once
    GET  /catalog/stock-check/{shop_id} — Check which catalog medicines a shop has in stock
"""

import json
from datetime import datetime, timezone, date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_client_info, require_role
from app.core.audit_hash import compute_audit_hash
from app.models.user import User, UserRole
from app.models.salt import Salt, ABCClass
from app.models.medicine import Medicine
from app.models.inventory import Inventory
from app.models.shop import Shop
from app.models.audit_log import AuditLog, ActionType
from app.core.medicine_catalog import MEDICINE_CATALOG

router = APIRouter(tags=["Medicine Catalog"])


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


def _find_or_create_salt(db: Session, salt_name: str, category: str) -> Salt:
    """Find a salt by formula_name or create it."""
    salt = db.execute(
        select(Salt).where(Salt.formula_name == salt_name)
    ).scalar_one_or_none()

    if not salt:
        salt = Salt(
            formula_name=salt_name,
            category=category,
        )
        db.add(salt)
        db.flush()

    return salt


def _find_or_create_medicine(
    db: Session,
    brand_name: str,
    salt_id: int,
    manufacturer: str | None,
    strength: str | None,
    form: str | None,
    unit_price: float | None,
    temp_sensitive: bool,
) -> Medicine:
    """Find a medicine by brand_name + salt_id or create it."""
    med = db.execute(
        select(Medicine).where(
            Medicine.brand_name == brand_name,
            Medicine.salt_id == salt_id,
            Medicine.is_active == True,
        )
    ).scalar_one_or_none()

    if not med:
        med = Medicine(
            brand_name=brand_name,
            salt_id=salt_id,
            manufacturer=manufacturer,
            strength=strength,
            dosage_form=form,
            unit_price=unit_price,
            temperature_sensitive=temp_sensitive,
        )
        db.add(med)
        db.flush()

    return med


# ── Pydantic Schemas ────────────────────────────────────────────

class CatalogItemResponse(BaseModel):
    """Schema for a single catalog item."""
    catalog_index: int
    brand_name: str
    salt_name: str
    category: str
    strength: str
    form: str
    manufacturer: str
    price: float
    temp_sensitive: bool
    abc_class: str
    reorder: int
    safety_stock: int
    critical: int


class CatalogListResponse(BaseModel):
    """Paginated catalog listing."""
    items: list[CatalogItemResponse]
    total: int
    page: int
    size: int


class CategoryCountResponse(BaseModel):
    """Category with medicine count."""
    category: str
    count: int


class QuickAddRequest(BaseModel):
    """Schema for quick-adding a catalog medicine to inventory."""
    catalog_index: int = Field(..., ge=0, description="Index in MEDICINE_CATALOG")
    shop_id: int = Field(..., gt=0, description="Shop to add inventory to")
    quantity: int = Field(..., gt=0, description="Number of units")
    batch_number: str = Field(..., min_length=1, description="Batch number")
    expiry_date: date = Field(..., description="Expiry date of this batch")
    cost_price: float = Field(..., ge=0, description="Purchase cost per unit")
    selling_price: float = Field(..., ge=0, description="Selling price per unit")


class BulkAddItem(BaseModel):
    """Schema for a single item in bulk-add."""
    catalog_index: int = Field(..., ge=0, description="Index in MEDICINE_CATALOG")
    quantity: int = Field(..., gt=0, description="Number of units")
    selling_price: float = Field(..., ge=0, description="Selling price per unit")


class BulkAddRequest(BaseModel):
    """Schema for bulk-adding catalog medicines to inventory."""
    shop_id: int = Field(..., gt=0, description="Shop to add inventory to")
    items: list[BulkAddItem] = Field(..., min_length=1, max_length=50)


class QuickAddResponse(BaseModel):
    """Response for quick-add."""
    id: int
    med_id: int
    shop_id: int
    quantity: int
    batch_number: str
    expiry_date: date
    cost_price: float | None
    selling_price: float | None
    brand_name: str | None = None
    salt_name: str | None = None
    shop_name: str | None = None

    model_config = {"from_attributes": True}


class BulkAddResponse(BaseModel):
    """Response for bulk-add."""
    added: list[QuickAddResponse]
    failed: list[dict]
    total_requested: int
    total_added: int


class StockCheckItem(BaseModel):
    """Schema for stock-check result."""
    catalog_index: int
    brand_name: str
    salt_name: str
    in_stock: bool
    current_quantity: int


# ── GET /catalog — Browse catalog with pagination ───────────────

@router.get("/", response_model=CatalogListResponse, summary="Browse medicine catalog")
def browse_catalog(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category"),
):
    """Browse the full medicine catalog with pagination and optional category filter."""
    if category:
        filtered = [m for m in MEDICINE_CATALOG if m["category"] == category]
    else:
        filtered = list(MEDICINE_CATALOG)

    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    page_items = filtered[start:end]

    items = []
    for i, med in enumerate(page_items):
        # Find the real catalog index
        real_index = MEDICINE_CATALOG.index(med)
        items.append(CatalogItemResponse(
            catalog_index=real_index,
            brand_name=med["brand_name"],
            salt_name=med["salt_name"],
            category=med["category"],
            strength=med["strength"],
            form=med["form"],
            manufacturer=med["manufacturer"],
            price=med["price"],
            temp_sensitive=med["temp_sensitive"],
            abc_class=med["abc_class"],
            reorder=med["reorder"],
            safety_stock=med["safety_stock"],
            critical=med["critical"],
        ))

    return CatalogListResponse(items=items, total=total, page=page, size=size)


# ── GET /catalog/search — Search catalog ───────────────────────

@router.get("/search", response_model=CatalogListResponse, summary="Search catalog")
def search_catalog(
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Search catalog by name, salt, manufacturer, or category."""
    query_lower = q.lower()
    results = []
    for med in MEDICINE_CATALOG:
        if (
            query_lower in med["brand_name"].lower()
            or query_lower in med["salt_name"].lower()
            or query_lower in med["manufacturer"].lower()
            or query_lower in med["category"].lower()
        ):
            results.append(med)

    total = len(results)
    start = (page - 1) * size
    end = start + size
    page_items = results[start:end]

    items = []
    for med in page_items:
        real_index = MEDICINE_CATALOG.index(med)
        items.append(CatalogItemResponse(
            catalog_index=real_index,
            brand_name=med["brand_name"],
            salt_name=med["salt_name"],
            category=med["category"],
            strength=med["strength"],
            form=med["form"],
            manufacturer=med["manufacturer"],
            price=med["price"],
            temp_sensitive=med["temp_sensitive"],
            abc_class=med["abc_class"],
            reorder=med["reorder"],
            safety_stock=med["safety_stock"],
            critical=med["critical"],
        ))

    return CatalogListResponse(items=items, total=total, page=page, size=size)


# ── GET /catalog/categories — List categories ──────────────────

@router.get("/categories", response_model=list[CategoryCountResponse], summary="List categories")
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List all categories with medicine count per category."""
    cat_counts: dict[str, int] = {}
    for med in MEDICINE_CATALOG:
        cat = med["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    return [
        CategoryCountResponse(category=cat, count=count)
        for cat, count in sorted(cat_counts.items(), key=lambda x: x[0])
    ]


# ── POST /catalog/quick-add — Add medicine from catalog ────────

@router.post(
    "/quick-add",
    response_model=QuickAddResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quick-add catalog medicine to inventory",
)
def quick_add(
    data: QuickAddRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
):
    """
    Add a medicine from the master catalog to a shop's inventory.
    Auto-creates the salt and medicine if they don't exist (upsert pattern).
    Admin/Pharmacist only.
    """
    # Validate catalog index
    if data.catalog_index < 0 or data.catalog_index >= len(MEDICINE_CATALOG):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog index {data.catalog_index} is out of range (0–{len(MEDICINE_CATALOG) - 1})",
        )

    catalog_item = MEDICINE_CATALOG[data.catalog_index]

    # Validate shop exists
    shop = db.execute(
        select(Shop).where(Shop.id == data.shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={data.shop_id} not found or inactive",
        )

    # Step 1: Find or create the salt
    salt = _find_or_create_salt(db, catalog_item["salt_name"], catalog_item["category"])

    # Step 2: Find or create the medicine
    med = _find_or_create_medicine(
        db=db,
        brand_name=catalog_item["brand_name"],
        salt_id=salt.id,
        manufacturer=catalog_item["manufacturer"],
        strength=catalog_item["strength"],
        form=catalog_item["form"],
        unit_price=catalog_item["price"],
        temp_sensitive=catalog_item["temp_sensitive"],
    )

    # Step 3: Create the inventory record
    inv = Inventory(
        med_id=med.id,
        shop_id=data.shop_id,
        quantity=data.quantity,
        batch_number=data.batch_number,
        expiry_date=data.expiry_date,
        cost_price=data.cost_price,
        selling_price=data.selling_price,
    )
    db.add(inv)
    db.flush()

    # Step 4: Create audit log
    _create_audit_log(
        db=db,
        action_type=ActionType.STOCK_ADDED,
        user_id=current_user.id,
        description=(
            f"Catalog quick-add: {catalog_item['brand_name']} at {shop.name}, "
            f"qty={data.quantity}, batch={data.batch_number}"
        ),
        details={
            "source": "catalog_quick_add",
            "catalog_index": data.catalog_index,
            "med_id": med.id,
            "shop_id": data.shop_id,
            "quantity": data.quantity,
            "batch_number": data.batch_number,
            "expiry_date": str(data.expiry_date),
            "cost_price": data.cost_price,
            "selling_price": data.selling_price,
        },
        resource_type="inventory",
        resource_id=inv.id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(inv)

    resp = QuickAddResponse.model_validate(inv)
    resp.brand_name = med.brand_name
    resp.salt_name = salt.formula_name
    resp.shop_name = shop.name
    return resp


# ── POST /catalog/bulk-add — Add multiple catalog medicines ────

@router.post(
    "/bulk-add",
    response_model=BulkAddResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk-add catalog medicines to inventory",
)
def bulk_add(
    data: BulkAddRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
):
    """
    Add multiple medicines from the catalog to a shop's inventory at once.
    Uses sensible defaults for batch_number and expiry_date.
    Admin/Pharmacist only.
    """
    # Validate shop
    shop = db.execute(
        select(Shop).where(Shop.id == data.shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={data.shop_id} not found or inactive",
        )

    added: list[QuickAddResponse] = []
    failed: list[dict] = []
    today = date.today()
    default_expiry = date(today.year + 1, today.month, today.day)

    for item in data.items:
        try:
            # Validate catalog index
            if item.catalog_index < 0 or item.catalog_index >= len(MEDICINE_CATALOG):
                failed.append({
                    "catalog_index": item.catalog_index,
                    "error": f"Index out of range (0–{len(MEDICINE_CATALOG) - 1})",
                })
                continue

            catalog_med = MEDICINE_CATALOG[item.catalog_index]

            # Find or create salt and medicine
            salt = _find_or_create_salt(db, catalog_med["salt_name"], catalog_med["category"])
            med = _find_or_create_medicine(
                db=db,
                brand_name=catalog_med["brand_name"],
                salt_id=salt.id,
                manufacturer=catalog_med["manufacturer"],
                strength=catalog_med["strength"],
                form=catalog_med["form"],
                unit_price=catalog_med["price"],
                temp_sensitive=catalog_med["temp_sensitive"],
            )

            inv = Inventory(
                med_id=med.id,
                shop_id=data.shop_id,
                quantity=item.quantity,
                batch_number=f"BULK-{date.today().strftime('%Y%m%d')}",
                expiry_date=default_expiry,
                cost_price=catalog_med["price"] * 0.7,  # estimated cost = 70% of retail
                selling_price=item.selling_price,
            )
            db.add(inv)
            db.flush()

            _create_audit_log(
                db=db,
                action_type=ActionType.STOCK_ADDED,
                user_id=current_user.id,
                description=(
                    f"Catalog bulk-add: {catalog_med['brand_name']} at {shop.name}, "
                    f"qty={item.quantity}"
                ),
                details={
                    "source": "catalog_bulk_add",
                    "catalog_index": item.catalog_index,
                    "med_id": med.id,
                    "shop_id": data.shop_id,
                    "quantity": item.quantity,
                    "selling_price": item.selling_price,
                },
                resource_type="inventory",
                resource_id=inv.id,
                client_info=client_info,
            )

            resp = QuickAddResponse.model_validate(inv)
            resp.brand_name = med.brand_name
            resp.salt_name = salt.formula_name
            resp.shop_name = shop.name
            added.append(resp)

        except Exception as e:
            failed.append({
                "catalog_index": item.catalog_index,
                "error": str(e),
            })

    db.commit()

    return BulkAddResponse(
        added=added,
        failed=failed,
        total_requested=len(data.items),
        total_added=len(added),
    )


# ── GET /catalog/stock-check/{shop_id} — Stock check ───────────

@router.get(
    "/stock-check/{shop_id}",
    response_model=list[StockCheckItem],
    summary="Check shop stock against catalog",
)
def stock_check(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    For each catalog medicine, show whether the shop has it in stock.
    Returns a list for quick order decisions.
    """
    # Validate shop
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={shop_id} not found or inactive",
        )

    # Get all inventory items for this shop
    inventory_items = db.execute(
        select(Inventory)
        .where(Inventory.shop_id == shop_id)
    ).scalars().all()

    # Build a map: med_id -> total quantity
    med_qty_map: dict[int, int] = {}
    for inv in inventory_items:
        med_qty_map[inv.med_id] = med_qty_map.get(inv.med_id, 0) + inv.quantity

    # Get all medicines with their brand_name and salt_id
    all_medicines = db.execute(
        select(Medicine, Salt.formula_name)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(Medicine.is_active == True)
    ).all()

    # Build maps for quick lookup
    med_brand_map: dict[int, str] = {}
    med_salt_map: dict[int, str] = {}  # med_id -> salt_name
    for med, salt_name in all_medicines:
        med_brand_map[med.id] = med.brand_name
        med_salt_map[med.id] = salt_name

    results = []
    for idx, catalog_item in enumerate(MEDICINE_CATALOG):
        # Find if any medicine in DB matches this catalog item's brand_name
        in_stock = False
        current_quantity = 0

        for med_id, qty in med_qty_map.items():
            brand = med_brand_map.get(med_id, "")
            if brand == catalog_item["brand_name"] and qty > 0:
                in_stock = True
                current_quantity += qty

        results.append(StockCheckItem(
            catalog_index=idx,
            brand_name=catalog_item["brand_name"],
            salt_name=catalog_item["salt_name"],
            in_stock=in_stock,
            current_quantity=current_quantity,
        ))

    return results


# ── GET /catalog/{index} — Get specific catalog item ───────────

@router.get("/{index}", response_model=CatalogItemResponse, summary="Get catalog item by index")
def get_catalog_item(
    index: int,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a specific catalog item by its index in the MEDICINE_CATALOG."""
    if index < 0 or index >= len(MEDICINE_CATALOG):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog index {index} is out of range (0–{len(MEDICINE_CATALOG) - 1})",
        )

    med = MEDICINE_CATALOG[index]
    return CatalogItemResponse(
        catalog_index=index,
        brand_name=med["brand_name"],
        salt_name=med["salt_name"],
        category=med["category"],
        strength=med["strength"],
        form=med["form"],
        manufacturer=med["manufacturer"],
        price=med["price"],
        temp_sensitive=med["temp_sensitive"],
        abc_class=med["abc_class"],
        reorder=med["reorder"],
        safety_stock=med["safety_stock"],
        critical=med["critical"],
    )
