"""
MediSebi — Shop Schemas
========================
Pydantic models for Shop CRUD operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ShopCreate(BaseModel):
    name: str = Field(..., max_length=150, description="Pharmacy/facility name")
    code: str = Field(..., max_length=20, description="Short alphanumeric code")
    address: str | None = Field(None, description="Full street address")
    city: str = Field(..., max_length=100, description="City")
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    latitude: float | None = Field(None)
    longitude: float | None = Field(None)
    contact_phone: str | None = Field(None, max_length=20)
    contact_email: str | None = Field(None, max_length=255)
    storage_capacity: int | None = Field(None, ge=0)


class ShopUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    code: str | None = Field(None, max_length=20)
    address: str | None = Field(None)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    latitude: float | None = Field(None)
    longitude: float | None = Field(None)
    contact_phone: str | None = Field(None, max_length=20)
    contact_email: str | None = Field(None, max_length=255)
    storage_capacity: int | None = Field(None, ge=0)


class ShopResponse(BaseModel):
    id: int
    name: str
    code: str
    address: str | None
    city: str
    state: str | None
    pincode: str | None
    latitude: float | None
    longitude: float | None
    contact_phone: str | None
    contact_email: str | None
    storage_capacity: int | None
    is_active: bool
    inventory_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ShopListResponse(BaseModel):
    items: list[ShopResponse]
    total: int
    page: int
    size: int
