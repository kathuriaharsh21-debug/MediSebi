"""
MediSebi — Billing Model
========================
Tracks customer bills (invoices) and line items.
Supports GST calculation, discounts, and multiple payment methods.
Each sale automatically decrements inventory (stock).
"""
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum as PyEnum

from app.core.database import Base
from app.core.mixins import TimestampMixin


class PaymentMethod(str, PyEnum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NET_BANKING = "net_banking"
    CREDIT = "credit"


class BillStatus(str, PyEnum):
    PAID = "paid"
    PENDING = "pending"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"
    __table_args__ = (
        Index("ix_bills_shop", "shop_id"),
        Index("ix_bills_created_by", "created_by"),
        Index("ix_bills_customer", "customer_name"),
        Index("ix_bills_date", "created_at"),
        {
            "comment": "Customer invoices. Each bill contains multiple line items.",
        },
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Invoice number: format "MED-YYYYMMDD-XXXX"
    invoice_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True,
        comment="Human-readable invoice number"
    )

    shop_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False,
        comment="Shop that generated this bill"
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        comment="User (pharmacist) who created the bill"
    )

    # Customer info
    customer_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Customer name (optional for walk-ins)"
    )
    customer_phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Customer phone number"
    )
    doctor_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Prescribing doctor (if applicable)"
    )

    # Financials
    subtotal: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="Sum before tax/discount"
    )
    discount_amount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="Total discount applied"
    )
    discount_percent: Mapped[float | None] = mapped_column(
        Float(5, 2), nullable=True, comment="Discount percentage (if percentage-based)"
    )
    cgst_amount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="CGST collected"
    )
    sgst_amount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="SGST collected"
    )
    total_amount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="Final payable amount"
    )
    amount_paid: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="Amount actually received"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BillStatus.PAID.value,
        comment="Bill status: paid, pending, cancelled, refunded"
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentMethod.CASH.value,
        comment="Payment method used"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional notes or prescription reference"
    )

    # Relationships
    shop = relationship("Shop", lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    items = relationship(
        "BillItem", back_populates="bill", lazy="joined",
        cascade="all, delete-orphan", order_by="BillItem.id"
    )

    def __repr__(self):
        return f"<Bill id={self.id} invoice={self.invoice_number} total=₹{self.total_amount}>"


class BillItem(Base, TimestampMixin):
    __tablename__ = "bill_items"
    __table_args__ = (
        Index("ix_bill_items_bill", "bill_id"),
        Index("ix_bill_items_inventory", "inventory_id"),
        {
            "comment": "Individual line items within a bill.",
        },
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False,
        comment="Parent bill"
    )
    inventory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventory.id", ondelete="RESTRICT"), nullable=False,
        comment="Inventory record from which stock was deducted"
    )
    med_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False,
        comment="Medicine sold (denormalized for performance)"
    )

    # Item details (snapshot at time of billing)
    medicine_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Medicine brand name (snapshot)"
    )
    salt_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Salt composition (snapshot)"
    )
    batch_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Batch number sold from"
    )
    expiry_date: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Expiry date (snapshot)"
    )

    # Quantities & pricing
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Quantity sold"
    )
    unit_price: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, comment="Selling price per unit at time of billing"
    )
    cost_price: Mapped[float | None] = mapped_column(
        Float(12, 2), nullable=True, comment="Cost price per unit (for profit calc)"
    )
    item_total: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="quantity * unit_price"
    )
    discount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="Line-item discount"
    )
    gst_rate: Mapped[float] = mapped_column(
        Float(5, 2), nullable=False, default=0.0, comment="GST rate applied (percentage)"
    )
    gst_amount: Mapped[float] = mapped_column(
        Float(12, 2), nullable=False, default=0.0, comment="GST amount for this item"
    )

    # Relationships
    bill = relationship("Bill", back_populates="items")
    inventory = relationship("Inventory", lazy="joined")
    medicine = relationship("Medicine", lazy="joined")

    def __repr__(self):
        return f"<BillItem id={self.id} med={self.medicine_name} qty={self.quantity}>"
