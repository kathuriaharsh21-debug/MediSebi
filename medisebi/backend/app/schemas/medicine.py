"""
MediSebi — Medicine Schemas
============================
Pydantic models for Medicine CRUD operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class MedicineCreate(BaseModel):
    brand_name: str = Field(..., max_length=150, description="Commercial brand name")
    salt_id: int = Field(..., gt=0, description="FK to active salt")
    generic_name: str | None = Field(None, max_length=150)
    manufacturer: str | None = Field(None, max_length=150)
    batch_prefix: str | None = Field(None, max_length=20)
    dosage_form: str | None = Field(None, max_length=50)
    strength: str | None = Field(None, max_length=50)
    unit_price: float | None = Field(None, ge=0)
    temperature_sensitive: bool = Field(False)
    min_storage_temp: float | None = Field(None)
    max_storage_temp: float | None = Field(None)
    description: str | None = Field(None)


class MedicineUpdate(BaseModel):
    brand_name: str | None = Field(None, max_length=150)
    salt_id: int | None = Field(None, gt=0)
    generic_name: str | None = Field(None, max_length=150)
    manufacturer: str | None = Field(None, max_length=150)
    batch_prefix: str | None = Field(None, max_length=20)
    dosage_form: str | None = Field(None, max_length=50)
    strength: str | None = Field(None, max_length=50)
    unit_price: float | None = Field(None, ge=0)
    temperature_sensitive: bool | None = Field(None)
    min_storage_temp: float | None = Field(None)
    max_storage_temp: float | None = Field(None)
    description: str | None = Field(None)


class MedicineResponse(BaseModel):
    id: int
    brand_name: str
    salt_id: int
    generic_name: str | None
    manufacturer: str | None
    dosage_form: str | None
    strength: str | None
    unit_price: float | None
    temperature_sensitive: bool
    salt_name: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class MedicineListResponse(BaseModel):
    items: list[MedicineResponse]
    total: int
    page: int
    size: int
