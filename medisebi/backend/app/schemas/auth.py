"""
MediSebi — Authentication Schemas
====================================
Pydantic models for request/response validation in auth endpoints.
"""

from pydantic import BaseModel, Field


# ── Request Schemas ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Registration data submitted by a new user."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username",
        examples=["pharmacist1"],
    )
    email: str = Field(
        ...,
        max_length=100,
        description="Email address",
        examples=["user@example.com"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Full display name",
        examples=["John Doe"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Password (must meet policy requirements)",
        examples=["SecureP@ssw0rd!"],
    )
    role: str = Field(
        "viewer",
        description="User role: admin, pharmacist, viewer",
    )


class LoginRequest(BaseModel):
    """Login credentials submitted by the user."""
    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Username for login",
        examples=["admin"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User password",
        examples=["SecureP@ssw0rd!"],
    )


class RefreshRequest(BaseModel):
    """Refresh token submitted to obtain a new token pair."""
    refresh_token: str = Field(
        ...,
        description="Raw JWT refresh token from a previous login or rotation",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class ChangePasswordRequest(BaseModel):
    """Password change request with current password verification."""
    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password to verify identity",
    )
    new_password: str = Field(
        ...,
        min_length=1,
        description="New password (must meet policy requirements)",
    )
    confirm_password: str = Field(
        ...,
        min_length=1,
        description="Confirmation of the new password (must match new_password)",
    )


# ── Response Schemas ────────────────────────────────────────────

class UserInfo(BaseModel):
    """Public user profile information returned in auth responses."""
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    mfa_enabled: bool

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Successful login response with JWT tokens and user info."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserInfo


class TokenResponse(BaseModel):
    """Token rotation response with new token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class PasswordPolicyResponse(BaseModel):
    """Password policy rules returned to the frontend for form validation."""
    min_length: int
    requires_uppercase: bool
    requires_lowercase: bool
    requires_digit: bool
    requires_special: bool
    history_count: int
