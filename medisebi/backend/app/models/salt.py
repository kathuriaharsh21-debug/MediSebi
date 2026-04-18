"""
MediSebi — Salt Model
======================
Active Pharmaceutical Ingredient (API) / Salt entity.
This is the LYNCHPIN of the substitution engine.
Multiple brand-name medicines can share the same salt_id,
enabling intelligent cross-brand substitution when a brand is out of stock.
"""

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TimestampMixin, SoftDeleteMixin


class Salt(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "salts"
    __table_args__ = {
        "comment": (
            "Active Pharmaceutical Ingredients (APIs). "
            "Multiple medicines share a salt → enables substitution logic."
        ),
    }

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

    # ── Relationships ───────────────────────────────────────
    medicines = relationship(
        "Medicine",
        back_populates="salt",
        lazy="select",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Salt id={self.id} formula='{self.formula_name}' category='{self.category}'>"
