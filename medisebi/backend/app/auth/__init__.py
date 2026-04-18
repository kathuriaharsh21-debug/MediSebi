"""
MediSebi — Authentication Package
===================================
Provides JWT token handling, password hashing, and FastAPI dependencies
for route protection and role-based access control (RBAC).
"""

from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    create_refresh_token_for_user,
    decode_access_token,
    decode_refresh_token,
)
from app.auth.password import hash_password, verify_password, needs_rehash
from app.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    get_client_info,
    oauth2_scheme,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "create_refresh_token_for_user",
    "decode_access_token",
    "decode_refresh_token",
    # Password
    "hash_password",
    "verify_password",
    "needs_rehash",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "get_client_info",
    "oauth2_scheme",
]
