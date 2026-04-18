"""
MediSebi — Salt-Based Substitution Engine
==========================================
Core substitution logic: find alternative medicines sharing the same salt
(active pharmaceutical ingredient) when a requested brand is out of stock.

This is the LYNCHPIN of MediSebi's intelligent pharmacy operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.medicine import Medicine
from app.models.salt import Salt
from app.models.inventory import Inventory
from app.models.shop import Shop
from app.schemas.substitution import (
    SubstitutionRequest,
    SubstitutionResponse,
    SubstitutionAlternative,
)

router = APIRouter(prefix="/substitution", tags=["Substitution"])


@router.post("/find-alternatives", response_model=SubstitutionResponse, summary="Find alternative medicines by salt")
def find_alternatives(
    data: SubstitutionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubstitutionResponse:
    """
    Find alternative medicines that share the same salt as the requested medicine.

    Steps:
      1. Look up the requested medicine → get its salt_id
      2. Find ALL other medicines with the same salt_id (is_active=True)
      3. For each alternative, check inventory at the requested shop_id
      4. Return only alternatives with quantity > 0, sorted by available_quantity DESC
      5. Include brand_name, available_quantity, expiry_date, unit_price
    """
    # Step 1: Look up requested medicine
    requested_med = db.execute(
        select(Medicine).where(
            Medicine.id == data.med_id,
            Medicine.is_active == True,
        )
    ).scalar_one_or_none()

    if not requested_med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine with id={data.med_id} not found or inactive",
        )

    # Step 2: Get the salt
    salt = db.execute(
        select(Salt).where(Salt.id == requested_med.salt_id)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Salt with id={requested_med.salt_id} not found (data integrity issue)",
        )

    # Step 3: Find shop
    shop = db.execute(
        select(Shop).where(Shop.id == data.shop_id, Shop.is_active == True)
    ).scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with id={data.shop_id} not found or inactive",
        )

    # Step 4: Find ALL active medicines with the same salt_id (including the requested one)
    # We include the requested medicine itself so the user can see its stock too
    all_medicines = db.execute(
        select(Medicine).where(
            Medicine.salt_id == requested_med.salt_id,
            Medicine.is_active == True,
        )
    ).scalars().all()

    med_ids = [m.id for m in all_medicines]

    if not med_ids:
        return SubstitutionResponse(
            requested_medicine=requested_med.brand_name,
            salt_name=salt.formula_name,
            alternatives=[],
            total_available=0,
        )

    # Step 5: For each medicine, check inventory at the requested shop
    inventory_items = db.execute(
        select(Inventory)
        .where(
            Inventory.med_id.in_(med_ids),
            Inventory.shop_id == data.shop_id,
            Inventory.quantity > 0,
        )
        .order_by(Inventory.quantity.desc())
    ).scalars().all()

    # Build alternatives
    alternatives: list[SubstitutionAlternative] = []
    total_available = 0

    for inv_item in inventory_items:
        med = next((m for m in all_medicines if m.id == inv_item.med_id), None)
        if med is None:
            continue

        alt = SubstitutionAlternative(
            medicine_id=med.id,
            brand_name=med.brand_name,
            salt_name=salt.formula_name,
            salt_id=salt.id,
            available_quantity=inv_item.quantity,
            expiry_date=inv_item.expiry_date,
            unit_price=inv_item.selling_price or med.unit_price,
            shop_name=shop.name,
        )
        alternatives.append(alt)
        total_available += inv_item.quantity

    return SubstitutionResponse(
        requested_medicine=requested_med.brand_name,
        salt_name=salt.formula_name,
        alternatives=alternatives,
        total_available=total_available,
    )


@router.get("/salt/{salt_id}/brands", summary="List all brands for a salt")
def list_salt_brands(
    salt_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    List all brand names for a given salt across all shops.
    Returns salt info and list of brands with their availability summary.
    """
    salt = db.execute(
        select(Salt).where(Salt.id == salt_id, Salt.is_active == True)
    ).scalar_one_or_none()

    if not salt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Salt with id={salt_id} not found or inactive",
        )

    # Get all active medicines for this salt
    medicines = db.execute(
        select(Medicine).where(
            Medicine.salt_id == salt_id,
            Medicine.is_active == True,
        )
    ).scalars().all()

    brands = []
    for med in medicines:
        # Get total stock across all shops
        total_stock = db.execute(
            select(func.sum(Inventory.quantity)).where(
                Inventory.med_id == med.id,
                Inventory.quantity > 0,
            )
        ).scalar() or 0

        # Get shops that have this medicine in stock
        stocked_shops = db.execute(
            select(Shop.id, Shop.name, Inventory.quantity)
            .join(Inventory, Inventory.shop_id == Shop.id)
            .where(Inventory.med_id == med.id, Inventory.quantity > 0)
        ).all()

        brands.append({
            "medicine_id": med.id,
            "brand_name": med.brand_name,
            "manufacturer": med.manufacturer,
            "dosage_form": med.dosage_form,
            "strength": med.strength,
            "unit_price": med.unit_price,
            "total_stock": total_stock,
            "available_in_shops": [
                {"shop_id": sid, "shop_name": sname, "quantity": qty}
                for sid, sname, qty in stocked_shops
            ],
        })

    return {
        "salt_id": salt.id,
        "salt_name": salt.formula_name,
        "category": salt.category,
        "total_brands": len(brands),
        "brands": brands,
    }
