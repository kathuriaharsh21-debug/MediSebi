"""
MediSebi — Shared SQLAlchemy Mixins
=====================================
Reusable mixins for common column patterns across all models.
Ensures consistency and reduces boilerplate.
"""

from datetime import datetime
from sqlalchemy import DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """
    Adds automatic `created_at` and `updated_at` timestamps.
    - `created_at` is set once on insert and never modified.
    - `updated_at` is auto-updated on every row modification via `onupdate`.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when this record was last updated",
    )


class SoftDeleteMixin:
    """
    Adds a soft-delete flag. Instead of physically deleting records,
    set `is_active = False` to preserve audit history.
    All queries should filter on `is_active == True` by default.
    """
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
        comment="Soft-delete flag. False = logically deleted.",
    )
