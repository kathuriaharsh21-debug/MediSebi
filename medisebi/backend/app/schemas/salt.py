"""
MediSebi — Salt Schemas
========================
Pydantic models for Salt CRUD operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.salt import ABCClass


class SaltCreate(BaseModel):
    formula_name: str = Field(..., max_length=100, description="Scientific/Generic name")
    description: str | None = Field(None, description="Pharmacological description")
    category: str = Field(..., max_length=50, description="Therapeutic category")
    atc_code: str | None = Field(None, max_length=20, description="WHO ATC code")
    dosage_form: str | None = Field(None, max_length=50, description="Standard dosage form")
    standard_strength: str | None = Field(None, max_length=50, description="Standard potency")
    unit_of_measure: str = Field("units", max_length=20, description="Quantity unit")
    abc_class: ABCClass = Field(ABCClass.C, description="ABC classification")
    reorder_level: int | None = Field(None, ge=0, description="Minimum reorder trigger level")
    safety_stock: int | None = Field(None, ge=0, description="Buffer stock quantity")
    critical_threshold: int | None = Field(None, ge=0, description="Critical alert threshold")
    warning_threshold: int | None = Field(None, ge=0, description="Warning alert threshold")


class SaltUpdate(BaseModel):
    formula_name: str | None = Field(None, max_length=100)
    description: str | None = Field(None)
    category: str | None = Field(None, max_length=50)
    atc_code: str | None = Field(None, max_length=20)
    dosage_form: str | None = Field(None, max_length=50)
    standard_strength: str | None = Field(None, max_length=50)
    unit_of_measure: str | None = Field(None, max_length=20)
    abc_class: ABCClass | None = Field(None)
    reorder_level: int | None = Field(None, ge=0)
    safety_stock: int | None = Field(None, ge=0)
    critical_threshold: int | None = Field(None, ge=0)
    warning_threshold: int | None = Field(None, ge=0)


class SaltResponse(BaseModel):
    id: int
    formula_name: str
    description: str | None
    category: str
    atc_code: str | None
    dosage_form: str | None
    standard_strength: str | None
    unit_of_measure: str
    abc_class: str
    reorder_level: int | None
    safety_stock: int | None
    critical_threshold: int | None
    warning_threshold: int | None
    is_active: bool
    medicines_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SaltListResponse(BaseModel):
    items: list[SaltResponse]
    total: int
    page: int
    size: int
