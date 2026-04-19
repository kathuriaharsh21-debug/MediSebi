"""
MediSebi — Substitution Schemas
================================
Pydantic models for the Salt-Based Substitution Engine.
"""

from datetime import date
from pydantic import BaseModel, Field


class SubstitutionRequest(BaseModel):
    med_id: int = Field(..., gt=0, description="Requested medicine ID")
    shop_id: int = Field(..., gt=0, description="Shop to search for alternatives")


class SubstitutionAlternative(BaseModel):
    medicine_id: int
    brand_name: str
    salt_name: str
    salt_id: int
    available_quantity: int
    expiry_date: date
    unit_price: float | None
    shop_name: str


class SubstitutionResponse(BaseModel):
    requested_medicine: str
    salt_name: str
    alternatives: list[SubstitutionAlternative]
    total_available: int
