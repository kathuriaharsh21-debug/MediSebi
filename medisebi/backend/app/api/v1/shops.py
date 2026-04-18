"""
MediSebi — Shops CRUD Router
=============================
REST endpoints for Shop management.
All write operations require ADMIN role and generate AuditLog entries.
"""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user, get_client_info, require_role
from app.core.audit_hash import compute_audit_hash
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.inventory import Inventory
from app.models.audit_log import AuditLog, ActionType
from app.schemas.shop import ShopCreate, ShopUpdate, ShopResponse, ShopListResponse

router = APIRouter(prefix="/shops", tags=["Shops"])


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


# ── LIST ──────────────────────────────────────────────────────
@router.get("/", response_model=ShopListResponse, summary="List all shops")
def list_shops(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    city: str | None = Query(None, description="Filter by city"),
) -> ShopListResponse:
    """List shops with pagination, optional city filter."""
    query = select(Shop).where(Shop.is_active == True)

    if city:
        query = query.where(Shop.city.ilike(f"%{city}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    items = db.execute(
        query.order_by(Shop.name.asc()).offset((page - 1) * size).limit(size)
    ).scalars().all()

    response_items = []
    for shop in items:
        inv_count = db.execute(
            select(func.count()).select_from(Inventory).where(Inventory.shop_id == shop.id)
        ).scalar() or 0
        resp = ShopResponse.model_validate(shop)
        resp.inventory_count = inv_count
        response_items.append(resp)

    return ShopListResponse(items=response_items, total=total, page=page, size=size)


# ── GET BY ID ─────────────────────────────────────────────────
@router.get("/{shop_id}", response_model=ShopResponse, summary="Get shop by ID")
def get_shop(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ShopResponse:
    """Get a single shop with its inventory count."""
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    inv_count = db.execute(
        select(func.count()).select_from(Inventory).where(Inventory.shop_id == shop.id)
    ).scalar() or 0

    resp = ShopResponse.model_validate(shop)
    resp.inventory_count = inv_count
    return resp


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=ShopResponse, status_code=status.HTTP_201_CREATED, summary="Create a new shop")
def create_shop(
    data: ShopCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> ShopResponse:
    """Create a new shop. Admin only."""
    # Check code uniqueness
    existing = db.execute(
        select(Shop).where(Shop.code == data.code)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shop with code '{data.code}' already exists",
        )

    shop = Shop(**data.model_dump())
    db.add(shop)
    db.flush()

    _create_audit_log(
        db=db,
        action_type=ActionType.SHOP_CREATED,
        user_id=current_user.id,
        description=f"Created shop '{data.name}' (code: {data.code})",
        details=data.model_dump(),
        resource_type="shop",
        resource_id=shop.id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(shop)
    return ShopResponse.model_validate(shop)


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{shop_id}", response_model=ShopResponse, summary="Update a shop")
def update_shop(
    shop_id: int,
    data: ShopUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> ShopResponse:
    """Update a shop. Admin only. Only provided fields are updated."""
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    update_data = data.model_dump(exclude_unset=True)

    # Check code uniqueness if changing
    if "code" in update_data:
        existing = db.execute(
            select(Shop).where(Shop.code == update_data["code"], Shop.id != shop_id)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shop with code '{update_data['code']}' already exists",
            )

    for field, value in update_data.items():
        setattr(shop, field, value)

    _create_audit_log(
        db=db,
        action_type=ActionType.SHOP_UPDATED,
        user_id=current_user.id,
        description=f"Updated shop '{shop.name}'",
        details=update_data,
        resource_type="shop",
        resource_id=shop_id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(shop)
    return ShopResponse.model_validate(shop)


# ── DELETE (soft) ─────────────────────────────────────────────
@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete a shop")
def delete_shop(
    shop_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> None:
    """Soft delete a shop (set is_active=False). Admin only."""
    shop = db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    db.execute(
        Shop.__table__.update()
        .where(Shop.id == shop_id)
        .values(is_active=False)
    )

    _create_audit_log(
        db=db,
        action_type=ActionType.SHOP_UPDATED,
        user_id=current_user.id,
        description=f"Soft-deleted shop '{shop.name}'",
        details={"name": shop.name, "code": shop.code},
        resource_type="shop",
        resource_id=shop_id,
        client_info=client_info,
    )

    db.commit()
