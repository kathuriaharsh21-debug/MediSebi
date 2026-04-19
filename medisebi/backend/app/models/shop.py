"""
MediSebi — Shop Model
======================
Represents a pharmacy or healthcare facility.
Multiple shops form the redistribution network.
The Smart Redistribution Engine scans across shops to optimize stock distribution.
"""

from sqlalchemy import String, Text, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TimestampMixin, SoftDeleteMixin


class Shop(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "shops"
    __table_args__ = {
        "comment": (
            "Pharmacy/healthcare facilities in the distribution network. "
            "The redistribution engine operates across these nodes."
        ),
    }

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique shop identifier",
    )

    # ── Identity ────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Official name of the pharmacy/facility",
    )
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Short alphanumeric code for internal reference (e.g., 'PH-NR-001')",
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full street address of the facility",
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="City for geographic grouping and climate-based predictions",
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="State or province",
    )
    pincode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        comment="PIN/ZIP code for precise geolocation mapping",
    )
    latitude: Mapped[float | None] = mapped_column(
        Float(9, 6),
        nullable=True,
        comment="Geographic latitude for OpenWeather API calls",
    )
    longitude: Mapped[float | None] = mapped_column(
        Float(9, 6),
        nullable=True,
        comment=" Geographic longitude for OpenWeather API calls",
    )
    contact_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Primary contact number",
    )
    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email for notifications and redistribution alerts",
    )

    # ── Capacity ────────────────────────────────────────────
    storage_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum storage units the facility can hold",
    )

    # ── Relationships ───────────────────────────────────────
    inventory_items = relationship(
        "Inventory",
        back_populates="shop",
        lazy="select",
        passive_deletes=True,
    )
    staff_assignments = relationship(
        "ShopStaff",
        back_populates="shop",
        lazy="select",
        passive_deletes=True,
    )
    transfer_requests_from = relationship(
        "StockTransferRequest",
        foreign_keys="StockTransferRequest.from_shop_id",
        back_populates="from_shop",
        lazy="select",
    )
    transfer_requests_to = relationship(
        "StockTransferRequest",
        foreign_keys="StockTransferRequest.to_shop_id",
        back_populates="to_shop",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Shop id={self.id} code='{self.code}' name='{self.name}'>"
