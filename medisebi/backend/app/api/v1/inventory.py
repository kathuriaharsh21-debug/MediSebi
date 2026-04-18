"""
MediSebi — Inventory CRUD Router
=================================
REST endpoints for Inventory management with optimistic locking.
All write operations generate AuditLog entries.
Admin and Pharmacist roles can perform write operations.
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime, timezone, date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_client_info, require_role
from app.core.audit_hash import compute_audit_hash
from app.models.user import User, UserRole
from app.models.inventory import Inventory
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.shop import Shop
from app.models.audit_log import AuditLog, ActionType
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryAdjustRequest,
    InventoryResponse,
    InventoryListResponse,
)

router = APIRouter(tags=["Inventory"])


# ── SCHEMA: Medicine scan result ──────────────────────
class MedicineScanResponse(BaseModel):
    brand_name: str | None = None
    salt_name: str | None = None
    manufacturer: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    batch_number: str | None = None
    expiry_date: str | None = None
    quantity: int | None = None
    mrp: float | None = None
    confidence: str = "extracted"  # or "partial" if many nulls


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
    """Helper: create an audit log entry with computed hash."""
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


def _enrich_inventory_response(db: Session, inv: Inventory) -> InventoryResponse:
    """Enrich an inventory item with medicine and shop names."""
    resp = InventoryResponse.model_validate(inv)
    if inv.medicine:
        resp.brand_name = inv.medicine.brand_name
        if inv.medicine.salt:
            resp.salt_name = inv.medicine.salt.formula_name
    if inv.shop:
        resp.shop_name = inv.shop.name
    return resp


# ── LIST ──────────────────────────────────────────────────────
@router.get("/", response_model=InventoryListResponse, summary="List inventory")
def list_inventory(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    med_id: int | None = Query(None, description="Filter by medicine ID"),
    shop_id: int | None = Query(None, description="Filter by shop ID"),
    expiring_within_days: int | None = Query(None, description="Filter items expiring within N days"),
    low_stock: bool = Query(False, description="Filter items below salt warning/critical threshold"),
) -> InventoryListResponse:
    """List inventory with optional filters for medicine, shop, expiry, and low stock."""
    query = select(Inventory)

    if med_id is not None:
        query = query.where(Inventory.med_id == med_id)

    if shop_id is not None:
        query = query.where(Inventory.shop_id == shop_id)

    if expiring_within_days is not None:
        cutoff = date.today() + timedelta(days=expiring_within_days)
        query = query.where(
            Inventory.expiry_date <= cutoff,
            Inventory.expiry_date >= date.today(),
        )

    if low_stock:
        # Join to salt through medicine to get thresholds
        # We'll filter in python after fetching since the join is complex
        query = query.join(Medicine, Inventory.med_id == Medicine.id).join(
            Salt, Medicine.salt_id == Salt.id
        )
        query = query.where(
            (Inventory.quantity <= Salt.warning_threshold)
            | (Inventory.quantity <= Salt.critical_threshold)
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    items = db.execute(
        query.order_by(Inventory.expiry_date.asc()).offset((page - 1) * size).limit(size)
    ).scalars().all()

    response_items = [_enrich_inventory_response(db, inv) for inv in items]
    return InventoryListResponse(items=response_items, total=total, page=page, size=size)


# ── ALERTS: EXPIRING SOON (before /{id} to avoid route capture) ──
@router.get("/alerts/expiring", response_model=InventoryListResponse, summary="Get expiring items")
def get_expiring_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Days within which items expire"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> InventoryListResponse:
    """Get inventory items expiring within N days."""
    cutoff = date.today() + timedelta(days=days)
    query = (
        select(Inventory)
        .where(Inventory.expiry_date >= date.today(), Inventory.expiry_date <= cutoff)
        .order_by(Inventory.expiry_date.asc())
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    items = db.execute(query.offset((page - 1) * size).limit(size)).scalars().all()
    response_items = [_enrich_inventory_response(db, inv) for inv in items]
    return InventoryListResponse(items=response_items, total=total, page=page, size=size)


# ── ALERTS: LOW STOCK (before /{id} to avoid route capture) ──────
@router.get("/alerts/low-stock", response_model=InventoryListResponse, summary="Get low-stock items")
def get_low_stock_items(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> InventoryListResponse:
    """
    Get inventory items below their salt's warning_threshold or critical_threshold.
    Items below critical_threshold appear first (most urgent).
    """
    query = (
        select(Inventory)
        .join(Medicine, Inventory.med_id == Medicine.id)
        .join(Salt, Medicine.salt_id == Salt.id)
        .where(
            (Inventory.quantity <= Salt.warning_threshold)
            | (Inventory.quantity <= Salt.critical_threshold)
        )
        .order_by(Inventory.quantity.asc())
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    items = db.execute(query.offset((page - 1) * size).limit(size)).scalars().all()
    response_items = []
    for inv in items:
        resp = _enrich_inventory_response(db, inv)
        if inv.medicine and inv.medicine.salt:
            salt = inv.medicine.salt
            if salt.critical_threshold is not None and inv.quantity <= salt.critical_threshold:
                resp.__dict__["_alert_level"] = "critical"
            elif salt.warning_threshold is not None and inv.quantity <= salt.warning_threshold:
                resp.__dict__["_alert_level"] = "warning"
        response_items.append(resp)
    return InventoryListResponse(items=response_items, total=total, page=page, size=size)


# ── SCAN MEDICINE FROM PHOTO ──────────────────────────────
@router.post("/scan-medicine", summary="Scan medicine from photo")
async def scan_medicine_from_photo(
    file: UploadFile = File(..., description="Photo of medicine packaging"),
    current_user: User = Depends(get_current_user),
) -> MedicineScanResponse:
    """
    Upload a photo of medicine packaging to auto-extract medicine details.
    Uses AI vision model to identify brand name, salt/active ingredient,
    batch number, expiry date, manufacturer, dosage form, and strength.

    Returns structured data that can be used to pre-fill the Add Stock form.
    """
    # Validate file is an image
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Only image files are accepted.",
        )

    # Save uploaded file to a temp directory
    tmp_dir = tempfile.mkdtemp()
    image_path = os.path.join(tmp_dir, file.filename or "scan_image.jpg")
    result_path = os.path.join(tmp_dir, "scan_result.json")

    try:
        contents = await file.read()
        with open(image_path, "wb") as f:
            f.write(contents)

        # Build the vision prompt
        prompt = (
            'You are a pharmacy assistant AI. Analyze this medicine packaging photo '
            'and extract the following information. Return ONLY valid JSON with these fields:\n'
            '- brand_name: The brand/product name (e.g., "Crocin 500mg", "Calpol 500mg")\n'
            '- salt_name: The active pharmaceutical ingredient / salt (e.g., "Paracetamol", "Amoxicillin")\n'
            '- manufacturer: The manufacturer/company name\n'
            '- strength: The strength/dosage (e.g., "500mg", "650mg")\n'
            '- dosage_form: The form (e.g., "Tablet", "Capsule", "Syrup", "Powder", "Injection")\n'
            '- batch_number: The batch/lot number if visible\n'
            '- expiry_date: The expiry date in YYYY-MM-DD format if visible\n'
            '- quantity: The quantity per pack if visible (e.g., 10, 15, 30)\n'
            '- mrp: The MRP/price if visible\n\n'
            'If a field is not visible or cannot be determined, use null. Be as accurate as possible. '
            'Only return JSON, no other text.'
        )

        # Run z-ai vision CLI
        cmd = ["z-ai", "vision", "-p", prompt, "-i", image_path, "-o", result_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if proc.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Vision analysis failed: {proc.stderr.strip() or 'Unknown error'}",
            )

        # Read the result JSON
        if not os.path.exists(result_path):
            # CLI succeeded but no output file — try to parse stdout
            raw = proc.stdout.strip()
            if not raw:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Vision analysis returned no output.",
                )
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return MedicineScanResponse(confidence="low")
        else:
            with open(result_path, "r") as f:
                raw = f.read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # JSON parsing failed — return partial
                return MedicineScanResponse(confidence="low")

        # Build response, mapping z-ai output fields to our schema
        null_count = sum(1 for v in data.values() if v is None)
        confidence = "partial" if null_count >= 5 else "extracted"

        return MedicineScanResponse(
            brand_name=data.get("brand_name"),
            salt_name=data.get("salt_name"),
            manufacturer=data.get("manufacturer"),
            strength=data.get("strength"),
            dosage_form=data.get("dosage_form"),
            batch_number=data.get("batch_number"),
            expiry_date=data.get("expiry_date"),
            quantity=data.get("quantity"),
            mrp=data.get("mrp"),
            confidence=confidence,
        )

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Vision analysis timed out. Please try again with a clearer image.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(exc)}",
        )
    finally:
        # Clean up temp files
        try:
            os.remove(image_path)
        except OSError:
            pass
        try:
            os.remove(result_path)
        except OSError:
            pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass


# ── GET BY ID ─────────────────────────────────────────────────
@router.get("/{inventory_id}", response_model=InventoryResponse, summary="Get inventory item by ID")
def get_inventory(
    inventory_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InventoryResponse:
    """Get a single inventory item with medicine and shop names."""
    inv = db.execute(
        select(Inventory).where(Inventory.id == inventory_id)
    ).scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    return _enrich_inventory_response(db, inv)


# ── CREATE (Add Stock) ────────────────────────────────────────
@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED, summary="Add stock")
def create_inventory(
    data: InventoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> InventoryResponse:
    """Add new inventory stock. Admin/Pharmacist only. Creates audit log."""
    # Validate medicine exists
    med = db.execute(
        select(Medicine).where(Medicine.id == data.med_id, Medicine.is_active == True)
    ).scalar_one_or_none()

    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with id={data.med_id} not found or inactive",
        )

    # Validate shop exists
    shop = db.execute(
        select(Shop).where(Shop.id == data.shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={data.shop_id} not found or inactive",
        )

    inv = Inventory(**data.model_dump())
    db.add(inv)
    db.flush()

    _create_audit_log(
        db=db,
        action_type=ActionType.STOCK_ADDED,
        user_id=current_user.id,
        description=f"Added stock: {med.brand_name} at {shop.name}, qty={data.quantity}",
        details={
            "med_id": data.med_id,
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
    return _enrich_inventory_response(db, inv)


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{inventory_id}", response_model=InventoryResponse, summary="Update inventory")
def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> InventoryResponse:
    """
    Update an inventory item. Admin/Pharmacist only.
    Uses optimistic locking via version_id — returns 409 on conflict.
    """
    inv = db.execute(
        select(Inventory).where(Inventory.id == inventory_id)
    ).scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    update_data = data.model_dump(exclude_unset=True)

    # Store the old version for the audit
    old_data = {
        "quantity": inv.quantity,
        "selling_price": inv.selling_price,
        "storage_location": inv.storage_location,
        "is_reserved": inv.is_reserved,
        "version_id": inv.version_id,
    }

    for field, value in update_data.items():
        setattr(inv, field, value)

    _create_audit_log(
        db=db,
        action_type=ActionType.STOCK_UPDATED,
        user_id=current_user.id,
        description=f"Updated inventory item id={inventory_id}",
        details={"old": old_data, "new": update_data},
        resource_type="inventory",
        resource_id=inventory_id,
        client_info=client_info,
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: inventory item was modified by another user. Please refresh and retry.",
        )

    db.refresh(inv)
    return _enrich_inventory_response(db, inv)


# ── ADJUST QUANTITY ──────────────────────────────────────────
@router.patch("/{inventory_id}/adjust", response_model=InventoryResponse, summary="Adjust inventory quantity")
def adjust_inventory(
    inventory_id: int,
    data: InventoryAdjustRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> InventoryResponse:
    """
    Atomically adjust quantity (add or subtract). Admin/Pharmacist only.
    Uses SQL-level atomic update to prevent race conditions.
    Negative adjustments that would drop below zero are rejected.
    """
    inv = db.execute(
        select(Inventory).where(Inventory.id == inventory_id)
    ).scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    adjustment = data.adjustment

    if adjustment == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment cannot be zero",
        )

    # For negative adjustments, check there's enough stock
    if adjustment < 0:
        new_qty = inv.quantity + adjustment
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Current: {inv.quantity}, attempting to remove: {abs(adjustment)}",
            )

    # Atomic update: only succeeds if version_id hasn't changed
    old_quantity = inv.quantity
    try:
        result = db.execute(
            update(Inventory)
            .where(
                Inventory.id == inventory_id,
                Inventory.version_id == inv.version_id,
            )
            .values(
                quantity=Inventory.quantity + adjustment,
                version_id=Inventory.version_id + 1,
            )
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: inventory item was modified by another user. Please refresh and retry.",
        )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: inventory item was modified by another user. Please refresh and retry.",
        )

    _create_audit_log(
        db=db,
        action_type=ActionType.STOCK_ADJUSTED,
        user_id=current_user.id,
        description=f"Adjusted inventory id={inventory_id} by {adjustment} (was {old_quantity})",
        details={
            "inventory_id": inventory_id,
            "adjustment": adjustment,
            "old_quantity": old_quantity,
            "new_quantity": old_quantity + adjustment,
        },
        resource_type="inventory",
        resource_id=inventory_id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(inv)
    return _enrich_inventory_response(db, inv)

