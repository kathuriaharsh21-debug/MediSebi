"""
MediSebi — Password History Model
====================================
Stores hashes of previous user passwords to prevent reuse.
Healthcare security best practice: users should not be able to
reuse their last 12 passwords. This prevents credential cycling
attacks where an attacker who gains access simply resets the
password to a previously known value.

DESIGN:
- Stores bcrypt hashes (same algorithm as the active password).
- On password change, the new hash is checked against ALL stored hashes.
- If a match is found, the change is rejected.
- Only the most recent N entries are kept (configurable, default 12).
- Old entries beyond the limit are pruned automatically.
"""

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base


class PasswordHistory(Base):
    """
    Password history entries for reuse prevention.
    Does NOT use TimestampMixin — only `created_at` matters here.
    No `updated_at` because these records are immutable once created.
    """
    __tablename__ = "password_history"
    __table_args__ = (
        Index("ix_ph_user_created", "user_id", "created_at"),
        {
            "comment": (
                "Historical password hashes to prevent reuse. "
                "Keeps the last N passwords per user. Immutable records."
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
        comment="User whose password history this belongs to",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hash of the previous password (same format as users.password_hash)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this password was set (and then changed)",
    )

    # ── Relationships ───────────────────────────────────────
    user = relationship(
        "User",
        back_populates="password_history",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<PasswordHistory id={self.id} user_id={self.user_id} date={self.created_at}>"
