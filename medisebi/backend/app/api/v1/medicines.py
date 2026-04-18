"""
MediSebi — Medicines CRUD Router
=================================
REST endpoints for Medicine management.
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
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.audit_log import AuditLog, ActionType
from app.schemas.medicine import MedicineCreate, MedicineUpdate, MedicineResponse, MedicineListResponse

router = APIRouter(prefix="/medicines", tags=["Medicines"])


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
@router.get("/", response_model=MedicineListResponse, summary="List all medicines")
def list_medicines(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    salt_id: int | None = Query(None, description="Filter by salt ID"),
    search: str | None = Query(None, description="Search by brand_name"),
) -> MedicineListResponse:
    """List medicines with pagination, optional salt_id filter and search."""
    query = select(Medicine).where(Medicine.is_active == True)

    if salt_id is not None:
        query = query.where(Medicine.salt_id == salt_id)

    if search:
        query = query.where(Medicine.brand_name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    items = db.execute(
        query.order_by(Medicine.brand_name.asc()).offset((page - 1) * size).limit(size)
    ).scalars().all()

    response_items = []
    for med in items:
        salt = db.execute(select(Salt).where(Salt.id == med.salt_id)).scalar_one_or_none()
        resp = MedicineResponse.model_validate(med)
        resp.salt_name = salt.formula_name if salt else None
        response_items.append(resp)

    return MedicineListResponse(items=response_items, total=total, page=page, size=size)


# ── GET BY ID ─────────────────────────────────────────────────
@router.get("/{medicine_id}", response_model=MedicineResponse, summary="Get medicine by ID")
def get_medicine(
    medicine_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MedicineResponse:
    """Get a single medicine with its salt name."""
    med = db.execute(
        select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active == True)
    ).scalar_one_or_none()

    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")

    salt = db.execute(select(Salt).where(Salt.id == med.salt_id)).scalar_one_or_none()
    resp = MedicineResponse.model_validate(med)
    resp.salt_name = salt.formula_name if salt else None
    return resp


# ── CREATE ────────────────────────────────────────────────────
@router.post("/", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED, summary="Create a new medicine")
def create_medicine(
    data: MedicineCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> MedicineResponse:
    """Create a new medicine. Admin only. Validates salt_id exists."""
    salt = db.execute(
        select(Salt).where(Salt.id == data.salt_id, Salt.is_active == True)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salt with id={data.salt_id} not found or inactive",
        )

    med = Medicine(**data.model_dump())
    db.add(med)
    db.flush()

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_CREATED,
        user_id=current_user.id,
        description=f"Created medicine '{data.brand_name}' (salt: {salt.formula_name})",
        details={**data.model_dump(), "salt_name": salt.formula_name},
        resource_type="medicine",
        resource_id=med.id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(med)
    resp = MedicineResponse.model_validate(med)
    resp.salt_name = salt.formula_name
    return resp


# ── UPDATE ────────────────────────────────────────────────────
@router.put("/{medicine_id}", response_model=MedicineResponse, summary="Update a medicine")
def update_medicine(
    medicine_id: int,
    data: MedicineUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> MedicineResponse:
    """Update a medicine. Admin only. Only provided fields are updated."""
    med = db.execute(
        select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active == True)
    ).scalar_one_or_none()

    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate salt_id if changing
    if "salt_id" in update_data:
        salt = db.execute(
            select(Salt).where(Salt.id == update_data["salt_id"], Salt.is_active == True)
        ).scalar_one_or_none()
        if not salt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Salt with id={update_data['salt_id']} not found or inactive",
            )

    for field, value in update_data.items():
        setattr(med, field, value)

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_UPDATED,
        user_id=current_user.id,
        description=f"Updated medicine '{med.brand_name}'",
        details=update_data,
        resource_type="medicine",
        resource_id=medicine_id,
        client_info=client_info,
    )

    db.commit()
    db.refresh(med)
    salt = db.execute(select(Salt).where(Salt.id == med.salt_id)).scalar_one_or_none()
    resp = MedicineResponse.model_validate(med)
    resp.salt_name = salt.formula_name if salt else None
    return resp


# ── DELETE (soft) ─────────────────────────────────────────────
@router.delete("/{medicine_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete a medicine")
def delete_medicine(
    medicine_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    client_info: Annotated[dict, Depends(get_client_info)],
) -> None:
    """Soft delete a medicine (set is_active=False). Admin only."""
    med = db.execute(
        select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active == True)
    ).scalar_one_or_none()

    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")

    db.execute(
        Medicine.__table__.update()
        .where(Medicine.id == medicine_id)
        .values(is_active=False)
    )

    _create_audit_log(
        db=db,
        action_type=ActionType.MEDICINE_DELETED,
        user_id=current_user.id,
        description=f"Soft-deleted medicine '{med.brand_name}'",
        details={"brand_name": med.brand_name, "salt_id": med.salt_id},
        resource_type="medicine",
        resource_id=medicine_id,
        client_info=client_info,
    )

    db.commit()
