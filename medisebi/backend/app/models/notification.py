"""
MediSebi — Notification Model
================================
In-app notification system for real-time alerts.
Implements the 3-tier alert system (CRITICAL / WARNING / INFO)
recommended by healthcare supply chain management best practices.

ALERT SOURCES:
- Expiry Watchdog: Medicines expiring within 30/15/7 days
- Demand Forecasting: Stock predicted to run out in 7 days
- Climate-Disease Engine: Weather-based disease risk alerts
- Redistribution Engine: Transfer requests requiring approval
- Inventory: Low stock / reorder threshold breached
- System: Security alerts (failed logins, suspicious activity)

DESIGN:
- Each notification targets a specific user (pharmacist or admin).
- Supports acknowledge/dismiss workflows for actionable alerts.
- Auto-generated notifications have a `source_type` for filtering.
- Notifications can link to specific resources (medicine, shop, transfer).
"""

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Index, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.mixins import TimestampMixin


class NotificationSeverity(str, enum.Enum):
    """
    3-tier alert severity matching healthcare supply chain standards.
    ──────────────────────────────────────────────────────────
    CRITICAL: Immediate action required. Treatment interruption risk.
    WARNING: Action needed soon. Auto-reorder should be triggered.
    INFO: Informational. Restocked, forecast updated, etc.
    """
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class NotificationSource(str, enum.Enum):
    """Source of the notification for dashboard filtering."""
    EXPIRY_WATCHDOG = "expiry_watchdog"
    DEMAND_FORECAST = "demand_forecast"
    CLIMATE_ENGINE = "climate_engine"
    REDISTRIBUTION = "redistribution"
    INVENTORY_ALERT = "inventory_alert"
    SYSTEM_SECURITY = "system_security"
    TRANSFER_REQUEST = "transfer_request"


class Notification(Base, TimestampMixin):
    """
    In-app notification records.
    Generated automatically by background services and manually by user actions.
    """
    __tablename__ = "notifications"
    __table_args__ = (
        # Dashboard query: "Show unread notifications for user X"
        Index("ix_notif_user_read", "user_id", "is_read"),
        # Filter query: "Show all critical notifications"
        Index("ix_notif_severity", "severity"),
        # Filter query: "Show all alerts from source X"
        Index("ix_notif_source", "source"),
        # Cleanup query: "Delete old read notifications"
        Index("ix_notif_created", "created_at"),
        {
            "comment": (
                "In-app 3-tier notification system for real-time alerts. "
                "Sources: expiry watchdog, demand forecast, climate engine, etc."
            ),
        },
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ── Target User ─────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Recipient of this notification",
    )

    # ── Content ─────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short notification title (shown in badge/list)",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full notification message with details and recommended action",
    )

    # ── Classification ──────────────────────────────────────
    severity: Mapped[NotificationSeverity] = mapped_column(
        default=NotificationSeverity.INFO,
        nullable=False,
        comment="Alert severity: critical (red), warning (yellow), info (green)",
    )
    source: Mapped[NotificationSource] = mapped_column(
        nullable=False,
        comment="System component that generated this notification",
    )

    # ── Linked Resource ─────────────────────────────────────
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of linked resource (e.g., 'inventory', 'transfer_request')",
    )
    resource_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="ID of the linked resource for direct navigation",
    )
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Frontend URL to navigate to when notification is clicked",
    )

    # ── Status ──────────────────────────────────────────────
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether the user has read this notification",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user read/dismissed this notification",
    )

    # ── Auto-cleanup ────────────────────────────────────────
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="After this date, the notification can be auto-pruned",
    )

    # ── Relationships ───────────────────────────────────────
    user = relationship(
        "User",
        back_populates="notifications",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} user_id={self.user_id} "
            f"severity={self.severity.value} title='{self.title[:40]}...'>"
        )
