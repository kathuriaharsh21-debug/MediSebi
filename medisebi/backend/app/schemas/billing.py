"""
MediSebi — Billing Schemas
===========================
Pydantic models for billing API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Bill Item Schemas ──────────────────────────────────────

class BillItemCreate(BaseModel):
    inventory_id: int = Field(..., description="Inventory record to deduct stock from")
    quantity: int = Field(..., gt=0, description="Quantity to sell")
    discount: float = Field(0.0, ge=0, description="Line-item discount in rupees")


class BillItemResponse(BaseModel):
    id: int
    inventory_id: int
    med_id: int
    medicine_name: str
    salt_name: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: int
    unit_price: float
    cost_price: Optional[float] = None
    item_total: float
    discount: float
    gst_rate: float
    gst_amount: float

    model_config = {"from_attributes": True}


# ── Bill Schemas ───────────────────────────────────────────

class BillCreate(BaseModel):
    shop_id: int = Field(..., description="Shop generating the bill")
    customer_name: Optional[str] = Field(None, max_length=100)
    customer_phone: Optional[str] = Field(None, max_length=20)
    doctor_name: Optional[str] = Field(None, max_length=100)
    discount_percent: Optional[float] = Field(None, ge=0, le=100, description="Overall discount %")
    payment_method: str = Field("cash", description="cash, upi, card, net_banking, credit")
    items: list[BillItemCreate] = Field(..., min_length=1, description="At least one item")
    notes: Optional[str] = None


class BillResponse(BaseModel):
    id: int
    invoice_number: str
    shop_id: int
    created_by: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    doctor_name: Optional[str] = None
    subtotal: float
    discount_amount: float
    discount_percent: Optional[float] = None
    cgst_amount: float
    sgst_amount: float
    total_amount: float
    amount_paid: float
    status: str
    payment_method: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    items: list[BillItemResponse] = []

    model_config = {"from_attributes": True}


class BillListResponse(BaseModel):
    items: list[BillResponse]
    total: int
    page: int
    size: int
    pages: int
