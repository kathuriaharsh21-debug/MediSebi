"""
MediSebi — Salts CRUD Router
=============================
REST endpoints for Salt management.
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
from app.models.salt import Salt
from app.models.medicine import Medicine
from app.models.audit_log import AuditLog, ActionType
from app.schemas.salt import SaltCreate, SaltUpdate, SaltResponse, SaltListResponse

router = APIRouter(prefix="/salts", tags=["Salts"])


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
@router.get("/", response_model=SaltListResponse, summary="List all salts")
def list_salts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by formula_name or category"),
) -> SaltListResponse:
    """List salts with pagination and optional search."""
    query = select(Salt).where(Salt.is_active == True)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Salt.formula_name.ilike(pattern)) | (Salt.category.ilike(pattern))
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    # Paginate
    items = db.execute(
        query.order_by(Salt.formula_name.asc()).offset((page - 1) * size).limit(size)
    ).scalars().all()

    # Enrich with medicines_count
    response_items = []
    for salt in items:
        med_count = db.execute(
            select(func.count()).select_from(Medicine).where(
                Medicine.salt_id == salt.id,
                Medicine.is_active == True,
            )
        ).scalar() or 0
        resp = SaltResponse.model_validate(salt)
        resp.medicines_count = med_count
        response_items.append(resp)

    return SaltListResponse(items=response_items, total=total, page=page, size=size)


# ── GET BY ID ─────────────────────────────────────────────────
@router.get("/{salt_id}", response_model=SaltResponse, summary="Get salt by ID")
def get_salt(
    salt_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SaltResponse:
    """Get a single salt with its medicines count."""
    salt = db.execute(
        select(Salt).where(Salt.id == salt_id, Salt.is_active == True)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salt not found")

    med_count = db.execute(
        select(func.count()).select_from(Medicine).where(
            Medicine.salt_id == salt.id,
            Medicine.is_active == True,
        )
    ).scalar() or 0

    resp = SaltResponse.model_validate(salt)
    resp.medicines_count = med_count
    return resp


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=SaltResponse, status_code=status.HTTP_201_CREATED, summary="Create a new salt")
def create_salt(
    data: SaltCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> SaltResponse:
    """Create a new salt. Admin only."""
    # Check uniqueness
    existing = db.execute(
        select(Salt).where(Salt.formula_name == data.formula_name)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Salt with formula_name '{data.formula_name}' already exists",
        )

    salt = Salt(**data.model_dump())
    db.add(salt)
    db.flush()

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_CREATED,  # Reuse: salt creation is akin to medicine-related
        user_id=current_user.id,
        description=f"Created salt '{data.formula_name}'",
        details=data.model_dump(),
        resource_type="salt",
        resource_id=salt.id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(salt)
    return SaltResponse.model_validate(salt)


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{salt_id}", response_model=SaltResponse, summary="Update a salt")
def update_salt(
    salt_id: int,
    data: SaltUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> SaltResponse:
    """Update a salt. Admin only. Only provided fields are updated."""
    salt = db.execute(
        select(Salt).where(Salt.id == salt_id, Salt.is_active == True)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salt not found")

    update_data = data.model_dump(exclude_unset=True)

    # Check formula_name uniqueness if changing
    if "formula_name" in update_data:
        existing = db.execute(
            select(Salt).where(
                Salt.formula_name == update_data["formula_name"],
                Salt.id != salt_id,
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Salt with formula_name '{update_data['formula_name']}' already exists",
            )

    for field, value in update_data.items():
        setattr(salt, field, value)

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_UPDATED,
        user_id=current_user.id,
        description=f"Updated salt '{salt.formula_name}'",
        details=update_data,
        resource_type="salt",
        resource_id=salt_id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(salt)
    return SaltResponse.model_validate(salt)


# ── DELETE (soft) ─────────────────────────────────────────────
@router.delete("/{salt_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete a salt")
def delete_salt(
    salt_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> None:
    """Soft delete a salt (set is_active=False). Admin only."""
    salt = db.execute(
        select(Salt).where(Salt.id == salt_id, Salt.is_active == True)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salt not found")

    db.execute(
        Salt.__table__.update()
        .where(Salt.id == salt_id)
        .values(is_active=False)
    )

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_DELETED,
        user_id=current_user.id,
        description=f"Soft-deleted salt '{salt.formula_name}'",
        details={"formula_name": salt.formula_name},
        resource_type="salt",
        resource_id=salt_id,
        client_info=client_info,
    )

    db.commit()
