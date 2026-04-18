"""
MediSebi — Audit Log Model
============================
Immutable, tamper-proof audit trail for all inventory mutations.
Every stock adjustment generates a SHA-256 hash of the transaction payload.
This hash is verified during any compliance audit to detect data tampering.

SECURITY NOTE: This table MUST NOT allow UPDATE or DELETE operations at the
database level. Enforce this via PostgreSQL triggers or row-level security.
"""

from sqlalchemy import String, Integer, BigInteger, DateTime, Text, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.mixins import TimestampMixin


class ActionType(str, enum.Enum):
    """
    Enumeration of all auditable actions in the system.
    Each new feature that mutates data MUST add its action type here.
    """
    # ── Inventory Operations ────────────────────────────────
    STOCK_ADDED = "stock_added"
    STOCK_UPDATED = "stock_updated"
    STOCK_REMOVED = "stock_removed"
    STOCK_TRANSFERRED = "stock_transferred"
    STOCK_ADJUSTED = "stock_adjusted"          # Manual correction
    STOCK_EXPIRED = "stock_expired"            # System-flagged expiry

    # ── Medicine Operations ─────────────────────────────────
    MEDICINE_CREATED = "medicine_created"
    MEDICINE_UPDATED = "medicine_updated"
    MEDICINE_DELETED = "medicine_deleted"       # Soft delete

    # ── User Operations ─────────────────────────────────────
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_LOCKED = "user_locked"
    USER_UNLOCKED = "user_unlocked"

    # ── Shop Operations ─────────────────────────────────────
    SHOP_CREATED = "shop_created"
    SHOP_UPDATED = "shop_updated"

    # ── System Operations ───────────────────────────────────
    SYSTEM_ALERT = "system_alert"
    REDISTRIBUTION_TRIGGERED = "redistribution_triggered"
    FORECAST_GENERATED = "forecast_generated"


class AuditLog(Base, TimestampMixin):
    """
    IMMUTABLE audit trail. Records are append-only.
    The `sha256_hash` field provides cryptographic proof of data integrity.
    Any modification to a record will invalidate its hash — detectable during audit.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        # Primary audit query: "Show all actions by user X"
        Index("ix_audit_user", "user_id"),
        # Forensic query: "What happened to this specific resource?"
        Index("ix_audit_resource", "resource_type", "resource_id"),
        # Compliance query: "All actions of a specific type"
        Index("ix_audit_action", "action_type"),
        # Time-range query: "All audit events in date range"
        Index("ix_audit_timestamp", "created_at"),
        {
            "comment": (
                "Immutable, cryptographically-hashed audit trail. "
                "Every inventory mutation and sensitive action is recorded here. "
                "INSERT ONLY — no updates or deletes permitted."
            ),
        },
    )

    # ── Primary Key ─────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Unique audit record identifier",
    )

    # ── Action Details ──────────────────────────────────────
    action_type: Mapped[ActionType] = mapped_column(
        SQLEnum(ActionType, name="action_type_enum", create_constraint=True),
        nullable=False,
        comment="Category of action performed",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description of what happened",
    )
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON payload with full before/after state of the affected record",
    )

    # ── Actor ───────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # NULL for system-triggered actions (e.g., expiry watchdog)
        comment="User who performed the action. NULL = system action.",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the client (supports IPv6 addresses)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Client user-agent string for forensic analysis",
    )

    # ── Target Resource ─────────────────────────────────────
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of affected resource (e.g., 'inventory', 'medicine', 'user')",
    )
    resource_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="ID of the affected resource record",
    )

    # ── Cryptographic Integrity ─────────────────────────────
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=False,
        comment=(
            "SHA-256 hash of (action_type + user_id + timestamp + details). "
            "Computed BEFORE insert. Any post-insert modification invalidates this hash."
        ),
    )

    # ── Relationships ───────────────────────────────────────
    user = relationship(
        "User",
        back_populates="audit_logs",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action_type.value} "
            f"user_id={self.user_id} hash={self.sha256_hash[:16]}...>"
        )
