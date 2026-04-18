"""
MediSebi — Notifications API Router
====================================
REST endpoints for the in-app 3-tier notification system.
Supports listing, reading, and deleting notifications.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.models.notification import Notification, NotificationSeverity, NotificationSource

router = APIRouter(tags=["Notifications"])


# ── Pydantic Schemas ──────────────────────────────────────────

class NotificationResponse(BaseModel):
    """Single notification returned to the client."""
    id: int
    user_id: int
    title: str
    message: str
    severity: NotificationSeverity
    source: NotificationSource
    resource_type: str | None = None
    resource_id: int | None = None
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with metadata."""
    items: list[NotificationResponse]
    total: int = Field(description="Total matching notifications")
    unread_count: int = Field(description="Total unread notifications for this user")
    page: int = Field(description="Current page number (1-based)")
    size: int = Field(description="Page size")


class UnreadCountResponse(BaseModel):
    """Unread notification count."""
    count: int = Field(description="Number of unread notifications")
    user_id: int = Field(description="User ID the count belongs to")


class MarkReadResponse(BaseModel):
    """Response after marking notification(s) as read."""
    detail: str
    notification_id: int | None = None


class MarkAllReadResponse(BaseModel):
    """Response after marking all notifications as read."""
    detail: str
    marked_count: int


class DeleteResponse(BaseModel):
    """Response after deleting a notification."""
    detail: str
    deleted_id: int


# ── Helpers ──────────────────────────────────────────────────

def _get_user_unread_count(db: Session, user_id: int) -> int:
    """Get total unread notification count for a user."""
    return (
        db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        .scalar()
        or 0
    )


# ── UNREAD COUNT ─────────────────────────────────────────────
@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
def get_unread_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadCountResponse:
    """Return the number of unread notifications for the authenticated user."""
    count = _get_user_unread_count(db, current_user.id)
    return UnreadCountResponse(count=count, user_id=current_user.id)


# ── MARK ALL READ ────────────────────────────────────────────
@router.put(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
)
def mark_all_read(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MarkAllReadResponse:
    """
    Mark all unread notifications as read for the authenticated user.
    Sets `is_read = True` and `read_at = now()` for every unread notification.
    """
    now = datetime.now(timezone.utc)

    # Determine how many rows will be affected
    count_q = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    marked_count = db.execute(count_q).scalar() or 0

    if marked_count > 0:
        db.execute(
            update(Notification)
            .where(Notification.user_id == current_user.id, Notification.is_read == False)
            .values(is_read=True, read_at=now)
        )
        db.commit()

    return MarkAllReadResponse(
        detail=f"Marked {marked_count} notification(s) as read.",
        marked_count=marked_count,
    )


# ── LIST NOTIFICATIONS ───────────────────────────────────────
@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="List notifications for current user",
)
def list_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    severity: NotificationSeverity | None = Query(None, description="Filter by severity level"),
    source: NotificationSource | None = Query(None, description="Filter by notification source"),
) -> NotificationListResponse:
    """
    Return a paginated list of notifications for the authenticated user.
    Results are sorted by `created_at` descending (newest first).
    """
    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    if severity is not None:
        query = query.where(Notification.severity == severity)

    if source is not None:
        query = query.where(Notification.source == source)

    # Total count for the filtered query
    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar() or 0

    # Unread count for the user (unfiltered)
    unread_count = _get_user_unread_count(db, current_user.id)

    # Fetch paginated results, newest first
    items = db.execute(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
        page=page,
        size=size,
    )


# ── MARK SINGLE NOTIFICATION AS READ ─────────────────────────
@router.put(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark a notification as read",
)
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MarkReadResponse:
    """
    Mark a single notification as read.
    The notification must belong to the authenticated user.
    """
    notification = db.execute(
        select(Notification).where(Notification.id == notification_id)
    ).scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this notification.",
        )

    if notification.is_read:
        return MarkReadResponse(
            detail="Notification is already marked as read.",
            notification_id=notification.id,
        )

    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)

    return MarkReadResponse(
        detail="Notification marked as read.",
        notification_id=notification.id,
    )


# ── DELETE NOTIFICATION (Admin only) ─────────────────────────
@router.delete(
    "/{notification_id}",
    response_model=DeleteResponse,
    summary="Delete a notification",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeleteResponse:
    """
    Delete a notification. **Admin only.**
    Physically removes the notification record from the database.
    """
    notification = db.execute(
        select(Notification).where(Notification.id == notification_id)
    ).scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.delete(notification)
    db.commit()

    return DeleteResponse(
        detail="Notification deleted successfully.",
        deleted_id=notification_id,
    )
