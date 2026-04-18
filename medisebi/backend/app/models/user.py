"""
MediSebi — User Model
======================
Stores authentication credentials and role-based access control data.
Passwords are stored as bcrypt hashes — never in plaintext.
"""

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base
from app.core.mixins import TimestampMixin, SoftDeleteMixin


class UserRole(str, enum.Enum):
    """
    System roles for Role-Based Access Control (RBAC).
    - ADMIN: Full system access — analytics, audit logs, user management.
    - PHARMACIST: Operational access — inventory CRUD, stock updates only.
    """
    ADMIN = "admin"
    PHARMACIST = "pharmacist"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = {
        "comment": "System users with RBAC roles for authentication and authorization",
    }

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique user identifier",
    )

    # ── Identity ────────────────────────────────────────────
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique login username (case-sensitive)",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address for notifications and recovery",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hash of user password. NEVER store plaintext.",
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name of the user",
    )

    # ── Authorization ───────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        default=UserRole.PHARMACIST,
        nullable=False,
        comment="RBAC role: admin or pharmacist",
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Account lock flag — set after too many failed login attempts",
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
        nullable=False,
        comment="Counter for consecutive failed login attempts",
    )
    last_login_at: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="ISO timestamp of last successful login",
    )

    # ── Relationships ───────────────────────────────────────
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        lazy="select",
    )
    shop_assignments = relationship(
        "ShopStaff",
        back_populates="user",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role={self.role.value}>"
