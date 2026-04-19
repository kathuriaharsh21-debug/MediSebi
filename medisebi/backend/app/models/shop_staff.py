"""
MediSebi — Shop Staff Assignment Model
========================================
Maps users (pharmacists) to their assigned shops.
A pharmacist can be assigned to multiple shops, and a shop can have
multiple pharmacists. This M:N relationship is critical for RBAC —
a pharmacist can only modify inventory at shops they are assigned to.
"""

from sqlalchemy import Integer, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date

from app.core.database import Base
from app.core.mixins import TimestampMixin


class ShopStaff(Base, TimestampMixin):
    """
    Junction table: Users ↔ Shops (Many-to-Many).
    Enforces that pharmacists can only operate within their assigned shops.
    """
    __tablename__ = "shop_staff"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "shop_id",
            name="uq_shop_staff_user_shop",
        ),
        Index("ix_shopstaff_shop", "shop_id"),
        {
            "comment": (
                "Maps pharmacists to their assigned shops. "
                "RBAC enforcement: users can only access inventory at assigned shops."
            ),
        },
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the user (pharmacist or admin)",
    )
    shop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the assigned shop",
    )
    assigned_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default="CURRENT_DATE",
        comment="Date when the user was assigned to this shop",
    )
    is_primary: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether this is the user's primary shop assignment",
    )

    # ── Relationships ───────────────────────────────────────
    user = relationship("User", back_populates="shop_assignments", lazy="joined")
    shop = relationship("Shop", back_populates="staff_assignments", lazy="joined")

    def __repr__(self) -> str:
        return f"<ShopStaff user_id={self.user_id} shop_id={self.shop_id}>"
