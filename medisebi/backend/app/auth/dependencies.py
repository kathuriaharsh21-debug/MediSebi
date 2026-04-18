"""
MediSebi — Authentication Dependencies
========================================
FastAPI dependencies for route protection, RBAC, and user context extraction.

Usage:
    @router.get("/profile")
    async def get_profile(user: User = Depends(get_current_active_user)):
        return user

    @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    async def admin_only():
        return {"message": "Admin access"}
"""

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.jwt_handler import decode_access_token
from app.models.user import User, UserRole

# ── OAuth2 Scheme ────────────────────────────────────────────────
# Token URL is the login endpoint; Swagger UI uses this for authentication.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT access token from the Authorization header.
    Returns the corresponding User ORM object.

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found.
    """
    payload = decode_access_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the authenticated user account is active (not soft-deleted).

    Raises:
        HTTPException 403: If user account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account. Contact administrator.",
        )
    return current_user


def require_role(*roles: UserRole) -> Callable:
    """
    Factory that returns a dependency enforcing role-based access control.

    Usage:
        @router.get("/admin-panel", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_panel():
            ...

        @router.get("/pharmacy", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.PHARMACIST))])
        async def pharmacy_data():
            ...

    Args:
        *roles: One or more UserRole values that are permitted.

    Returns:
        Dependency function that validates the user's role.
    """

    def _check_role(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(r.value for r in roles)}.",
            )
        return current_user

    return _check_role


def get_client_info(request: Request) -> dict:
    """
    Extract client IP address and User-Agent from the request.

    Returns:
        Dict with 'ip_address' and 'user_agent' keys.
    """
    # X-Forwarded-For is set by reverse proxies (nginx, Caddy, etc.)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    user_agent = request.headers.get("User-Agent", "unknown")

    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
