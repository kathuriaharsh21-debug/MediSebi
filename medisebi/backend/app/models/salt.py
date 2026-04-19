"""
MediSebi — Salt Model
======================
Active Pharmaceutical Ingredient (API) / Salt entity.
This is the LYNCHPIN of the substitution engine.
Multiple brand-name medicines can share the same salt_id,
enabling intelligent cross-brand substitution when a brand is out of stock.

IMPROVEMENTS (Post-Research):
- Added reorder_level + safety_stock for automatic reorder automation
- Added unit_of_measure for quantity standardization
- Added abc_class (ABC Analysis) for inventory prioritization
- Added alert thresholds (critical/warning) for 3-tier notification system
"""

from sqlalchemy import String, Text, Integer, Float, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.core.mixins import TimestampMixin, SoftDeleteMixin


class ABCClass(str, enum.Enum):
    """
    ABC Inventory Classification — industry-standard pharmacy inventory method.
    ─────────────────────────────────────────────────────────
    - A: High-value / high-turnover items (~20% of SKUs, ~80% of revenue).
      Require tight control, frequent review, and accurate forecasting.
    - B: Medium-value items (~30% of SKUs, ~15% of revenue).
      Moderate control, periodic review.
    - C: Low-value / low-turnover items (~50% of SKUs, ~5% of revenue).
      Minimal control, bulk ordering, simple monitoring.
    """
    A = "a"  # Critical — tight control
    B = "b"  # Moderate — periodic review
    C = "c"  # Low — minimal control


class Salt(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "salts"
    __table_args__ = (
        Index("ix_salt_abc_class", "abc_class"),
        {
            "comment": (
                "Active Pharmaceutical Ingredients (APIs). "
                "Multiple medicines share a salt → enables substitution logic. "
                "Includes reorder automation and ABC classification."
            ),
        },
    )

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique salt identifier",
    )

    # ── Identity ────────────────────────────────────────────
    formula_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Scientific/Generic name (e.g., 'Paracetamol', 'Amoxicillin')",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the salt's pharmacological properties",
    )
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Therapeutic category (e.g., 'Analgesic', 'Antibiotic', 'ORS')",
    )
    atc_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="WHO Anatomical Therapeutic Chemical classification code",
    )
    dosage_form: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Standard dosage form (e.g., 'Tablet', 'Syrup', 'Capsule')",
    )
    standard_strength: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Standard potency (e.g., '500mg', '250mg/5ml')",
    )

    # ── Inventory Intelligence (Ease of Use) ────────────────
    unit_of_measure: Mapped[str] = mapped_column(
        String(20),
        default="units",
        server_default="units",
        nullable=False,
        comment="Standard unit for quantity (e.g., 'tablets', 'bottles', 'vials', 'strips')",
    )
    abc_class: Mapped[ABCClass] = mapped_column(
        default=ABCClass.C,
        nullable=False,
        comment="ABC inventory classification: A=critical, B=moderate, C=low-priority",
    )
    reorder_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Minimum stock level that triggers a reorder. "
            "Calculated as: (avg_daily_usage x lead_time_days) + safety_stock"
        ),
    )
    safety_stock: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Buffer stock to prevent stockouts during supply delays. "
            "Typically 1-2 weeks of average usage."
        ),
    )
    critical_threshold: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "CRITICAL alert threshold. Stock at or below this level = "
            "treatment interruption risk. Triggers immediate red alert."
        ),
    )
    warning_threshold: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "WARNING alert threshold. Stock at or below this level = "
            "auto-reorder should be triggered. Yellow alert on dashboard."
        ),
    )

    # ── Relationships ───────────────────────────────────────
    medicines = relationship(
        "Medicine",
        back_populates="salt",
        lazy="select",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Salt id={self.id} formula='{self.formula_name}' "
            f"category='{self.category}' abc={self.abc_class.value}>"
        )
