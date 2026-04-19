"""
MediSebi — Medicine Model
==========================
Brand-name medicines linked to their active pharmaceutical ingredient (Salt).
One salt can have multiple brand-name medicines (e.g., Paracetamol → Crocin, Calpol, Dolo).
This is the foundation for the salt-based substitution engine.
"""

from sqlalchemy import String, Boolean, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TimestampMixin, SoftDeleteMixin


class Medicine(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "medicines"
    __table_args__ = {
        "comment": (
            "Brand-name medicines mapped to their active salt. "
            "Multiple brands per salt enable substitution when one brand is unavailable."
        ),
    }

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique medicine identifier",
    )

    # ── Identity ────────────────────────────────────────────
    brand_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Commercial brand name (e.g., 'Crocin 500mg')",
    )
    generic_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Generic display name if different from brand",
    )
    manufacturer: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Manufacturing company name",
    )
    batch_prefix: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Batch number prefix pattern used by the manufacturer",
    )

    # ── Salt Linkage ────────────────────────────────────────
    salt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("salts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Foreign key to the active pharmaceutical ingredient (salt)",
    )

    # ── Physical Properties ─────────────────────────────────
    dosage_form: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Form factor: Tablet, Capsule, Syrup, Injection, etc.",
    )
    strength: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Potency specification (e.g., '500mg', '250mg/5ml')",
    )
    unit_price: Mapped[float | None] = mapped_column(
        Float(10, 2),
        nullable=True,
        comment="Base unit price in INR (or configured currency)",
    )
    temperature_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Flag for cold-chain logistics: True if medicine requires temperature control",
    )
    min_storage_temp: Mapped[float | None] = mapped_column(
        Float(4, 2),
        nullable=True,
        comment="Minimum storage temperature in Celsius (for cold-chain items)",
    )
    max_storage_temp: Mapped[float | None] = mapped_column(
        Float(4, 2),
        nullable=True,
        comment="Maximum storage temperature in Celsius (for cold-chain items)",
    )

    # ── Metadata ────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Brief description or notes about the medicine",
    )

    # ── Relationships ───────────────────────────────────────
    salt = relationship(
        "Salt",
        back_populates="medicines",
        lazy="joined",
    )
    inventory_items = relationship(
        "Inventory",
        back_populates="medicine",
        lazy="select",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Medicine id={self.id} brand='{self.brand_name}' salt_id={self.salt_id}>"
