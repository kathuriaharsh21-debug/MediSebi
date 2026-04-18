"""
MediSebi — Inventory Schemas
=============================
Pydantic models for Inventory CRUD operations.
"""

from datetime import date, datetime
from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    med_id: int = Field(..., gt=0, description="FK to medicine")
    shop_id: int = Field(..., gt=0, description="FK to shop")
    quantity: int = Field(..., ge=0, description="Stock quantity")
    batch_number: str | None = Field(None, max_length=50)
    expiry_date: date = Field(..., description="Expiry date")
    cost_price: float | None = Field(None, ge=0)
    selling_price: float | None = Field(None, ge=0)
    storage_location: str | None = Field(None, max_length=50)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(None, ge=0)
    selling_price: float | None = Field(None, ge=0)
    storage_location: str | None = Field(None, max_length=50)
    is_reserved: bool | None = Field(None)


class InventoryAdjustRequest(BaseModel):
    adjustment: int = Field(
        ...,
        description="Quantity to add (positive) or subtract (negative). Must result in >= 0.",
    )


class InventoryResponse(BaseModel):
    id: int
    med_id: int
    shop_id: int
    quantity: int
    batch_number: str | None
    expiry_date: date
    cost_price: float | None
    selling_price: float | None
    version_id: int
    is_reserved: bool
    storage_location: str | None
    brand_name: str | None = None
    salt_name: str | None = None
    shop_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class InventoryListResponse(BaseModel):
    items: list[InventoryResponse]
    total: int
    page: int
    size: int
