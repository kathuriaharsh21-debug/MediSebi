"""
MediSebi — Inventory Model
===========================
Tracks real-time stock levels for each medicine at each shop.
This is the most frequently queried table — indexes are critical.
Expiry tracking and demand forecasting both depend on this data.
"""

from sqlalchemy import String, Integer, Date, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date

from app.core.database import Base
from app.core.mixins import TimestampMixin


class Inventory(Base, TimestampMixin):
    """
    Real-time stock ledger with OPTIMISTIC LOCKING.
    ─────────────────────────────────────────────────
    The `version_id` column prevents race conditions when two users
    modify the same inventory record simultaneously. SQLAlchemy
    automatically appends `WHERE version_id = :old_version` to UPDATEs.
    If 0 rows are affected (someone else modified it first), a
    `StaleDataError` is raised — forcing the caller to retry.

    NOTE: No soft-delete — inventory records are immutable financial data.
    Adjustments are tracked via Audit_Logs, not by deleting records.
    """
    __tablename__ = "inventory"
    __table_args__ = (
        # Composite index for the most common query pattern:
        # "Find all inventory for a medicine at a specific shop"
        Index(
            "ix_inventory_med_shop",
            "med_id", "shop_id",
        ),
        # Composite index for the substitution engine:
        # "Find all shops that have stock of medicine X"
        Index(
            "ix_inventory_med_quantity",
            "med_id", "quantity",
        ),
        # Critical index for the Expiry Watchdog:
        # "Find all items expiring within N days"
        Index(
            "ix_inventory_expiry",
            "expiry_date",
        ),
        # Index for redistribution engine queries:
        Index(
            "ix_inventory_shop_quantity",
            "shop_id", "quantity",
        ),
        {
            "comment": (
                "Real-time stock ledger. Each row represents one medicine batch "
                "at one shop location. Adjustments are audited, never deleted."
            ),
        },
    )

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique inventory record identifier",
    )

    # ── Foreign Keys ────────────────────────────────────────
    med_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("medicines.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to the medicine being tracked",
    )
    shop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shops.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to the shop holding this stock",
    )

    # ── Stock Data ──────────────────────────────────────────
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current stock quantity. Updated only via audited transactions.",
    )
    batch_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Manufacturer batch number for traceability",
    )
    expiry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date after which this stock MUST NOT be dispensed",
    )
    cost_price: Mapped[float | None] = mapped_column(
        Float(10, 2),
        nullable=True,
        comment="Purchase cost per unit",
    )
    selling_price: Mapped[float | None] = mapped_column(
        Float(10, 2),
        nullable=True,
        comment="Selling price per unit at this shop",
    )

    # ── Optimistic Locking (Security) ─────────────────────
    version_id: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
        comment=(
            "Optimistic lock version. Auto-incremented on each UPDATE. "
            "Prevents race conditions in concurrent stock modifications."
        ),
    )

    # ── Status Flags ────────────────────────────────────────
    is_reserved: Mapped[bool] = mapped_column(
        # No default — explicit intent required
        default=False,
        server_default="false",
        nullable=False,
        comment="True if this batch is reserved for a pending transfer or order",
    )
    storage_location: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Physical storage location identifier (e.g., 'Shelf-A3', 'Fridge-02')",
    )

    # ── Relationships ───────────────────────────────────────
    medicine = relationship(
        "Medicine",
        back_populates="inventory_items",
        lazy="joined",
    )
    shop = relationship(
        "Shop",
        back_populates="inventory_items",
        lazy="joined",
    )

    # ── SQLAlchemy Mapper Args for Optimistic Locking ─────
    __mapper_args__ = {
        "version_id_col": version_id,
    }

    def __repr__(self) -> str:
        return (
            f"<Inventory id={self.id} med_id={self.med_id} "
            f"shop_id={self.shop_id} qty={self.quantity} "
            f"expires={self.expiry_date} v={self.version_id}>"
        )
