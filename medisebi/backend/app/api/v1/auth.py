"""
MediSebi — Authentication API Endpoints
=========================================
Implements login, token refresh, logout, password management, and user info.

Security Features:
- Account lockout after N failed login attempts
- Refresh token rotation with family-based revocation
- Password history enforcement (last N passwords)
- Audit logging for all authentication events
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.token_utils import (
    hash_token,
    verify_token_hash,
    generate_token_family_id,
    generate_device_fingerprint,
)
from app.core.password_validator import PasswordValidator
from app.core.audit_hash import compute_audit_hash
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.password_history import PasswordHistory
from app.models.audit_log import AuditLog, ActionType
from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token_for_user,
    decode_refresh_token,
)
from app.auth.password import hash_password, verify_password, needs_rehash
from app.auth.dependencies import (
    get_current_active_user,
    get_client_info,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    UserInfo,
    ChangePasswordRequest,
    PasswordPolicyResponse,
)

router = APIRouter()


# ════════════════════════════════════════════════════════════════
# Helper: Create Audit Log Entry
# ════════════════════════════════════════════════════════════════

def _create_audit_log(
    db: Session,
    action_type: ActionType,
    user_id: int | None,
    description: str,
    details: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Create and persist an AuditLog entry with SHA-256 integrity hash.
    """
    now = datetime.now(timezone.utc).isoformat()
    sha256_hash = compute_audit_hash(
        action_type=action_type.value,
        user_id=user_id,
        timestamp=now,
        details=details,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    entry = AuditLog(
        action_type=action_type,
        description=description,
        details=details,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        resource_type=resource_type,
        resource_id=resource_id,
        sha256_hash=sha256_hash,
    )
    db.add(entry)
    db.flush()
    return entry


# ════════════════════════════════════════════════════════════════
# POST /auth/login
# ════════════════════════════════════════════════════════════════

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and return JWT token pair.

    On failure: increment failed_login_attempts. After N failures, lock account.
    On success: reset counter, update last_login_at, issue tokens.
    """
    client = get_client_info(request)
    ip_address = client["ip_address"]
    user_agent = client["user_agent"]

    # Look up user by username
    user = db.query(User).filter(User.username == body.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Check if account is locked
    if user.is_locked:
        # Auto-unlock if lockout duration has passed
        if user.locked_at:
            lockout_delta = timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            if datetime.now(timezone.utc) >= user.locked_at + lockout_delta:
                user.is_locked = False
                user.failed_login_attempts = 0
                user.locked_at = None
            else:
                _create_audit_log(
                    db=db,
                    action_type=ActionType.USER_LOGIN,
                    user_id=user.id,
                    description=f"Login attempt while account locked for user '{user.username}'",
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Account is locked due to too many failed login attempts. "
                        f"Try again after {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes "
                        f"or contact an administrator."
                    ),
                )
        else:
            _create_audit_log(
                db=db,
                action_type=ActionType.USER_LOGIN,
                user_id=user.id,
                description=f"Login attempt while account locked for user '{user.username}'",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Account is locked due to too many failed login attempts. "
                    f"Try again after {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes "
                    f"or contact an administrator."
                ),
            )

    # Verify password
    if not verify_password(body.password, user.password_hash):
        # Increment failed attempt counter
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            user.is_locked = True
            user.locked_at = datetime.now(timezone.utc)
            _create_audit_log(
                db=db,
                action_type=ActionType.USER_LOCKED,
                user_id=user.id,
                description=(
                    f"User '{user.username}' locked after "
                    f"{user.failed_login_attempts} failed login attempts."
                ),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Account locked after {settings.ACCOUNT_LOCKOUT_THRESHOLD} "
                    f"failed login attempts. Contact an administrator."
                ),
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # ── Successful Authentication ──────────────────────────────
    # Reset failed attempts
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)

    # Opportunistic rehash if bcrypt rounds changed
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_raw, refresh_hash = create_refresh_token_for_user(user.id)

    # Store refresh token in database
    family_id = generate_token_family_id()
    refresh_token_record = RefreshToken(
        token_hash=refresh_hash,
        token_family_id=family_id,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        device_fingerprint=generate_device_fingerprint(user_agent, ip_address),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(refresh_token_record)

    # Audit log
    _create_audit_log(
        db=db,
        action_type=ActionType.USER_LOGIN,
        user_id=user.id,
        description=f"User '{user.username}' logged in successfully.",
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_raw,
        token_type="Bearer",
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            mfa_enabled=user.mfa_enabled,
        ),
    )


# ════════════════════════════════════════════════════════════════
# POST /auth/refresh
# ════════════════════════════════════════════════════════════════

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Rotate a refresh token and issue a new token pair.

    Flow:
    1. Decode the raw refresh token (JWT validation).
    2. Hash it and look it up in the database.
    3. If valid & not revoked → revoke old, issue new in same family.
    4. If already revoked with reason="rotation" → REUSE DETECTED → revoke entire family.
    5. If already revoked with reason="logout" → normal logout, return 401.
    6. If not found → invalid token, return 401.
    """
    client = get_client_info(request)

    # Step 1: Decode the JWT
    payload = decode_refresh_token(body.refresh_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing user identifier.",
        )

    # Step 2: Hash and look up in database
    token_hash = hash_token(body.refresh_token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    # Step 6: Not found
    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. Please log in again.",
        )

    # Step 3: Already revoked
    if stored_token.is_revoked:
        # Step 4: Reuse detected — revoke entire family
        if stored_token.revoked_reason == "rotation":
            # Token theft suspected — revoke ALL tokens in this family
            family_tokens = (
                db.query(RefreshToken)
                .filter(
                    RefreshToken.token_family_id == stored_token.token_family_id,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
                .all()
            )
            now = datetime.now(timezone.utc)
            for token in family_tokens:
                token.is_revoked = True
                token.revoked_at = now
                token.revoked_reason = "theft_detected"

            _create_audit_log(
                db=db,
                action_type=ActionType.USER_LOGIN,
                user_id=int(user_id),
                description=(
                    f"Refresh token reuse detected. "
                    f"Entire token family '{stored_token.token_family_id}' revoked."
                ),
                ip_address=client["ip_address"],
                user_agent=client["user_agent"],
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected. All sessions revoked for security. Please log in again.",
            )

        # Step 5: Normal logout
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked. Please log in again.",
        )

    # Step 3: Valid token — perform rotation
    now = datetime.now(timezone.utc)

    # Revoke the old token
    stored_token.is_revoked = True
    stored_token.revoked_at = now
    stored_token.revoked_reason = "rotation"

    # Create new refresh token in the same family
    new_refresh_raw, new_refresh_hash = create_refresh_token_for_user(int(user_id))
    new_token_record = RefreshToken(
        token_hash=new_refresh_hash,
        token_family_id=stored_token.token_family_id,
        user_id=stored_token.user_id,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        device_fingerprint=generate_device_fingerprint(client["user_agent"], client["ip_address"]),
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )
    db.add(new_token_record)

    # Create new access token
    access_token = create_access_token(data={"sub": str(user_id)})

    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_raw,
        token_type="Bearer",
    )


# ════════════════════════════════════════════════════════════════
# POST /auth/logout
# ════════════════════════════════════════════════════════════════

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Revoke the current refresh token family (full session logout).

    Accepts a refresh_token in the body and revokes ALL tokens in its family.
    """
    client = get_client_info(request)

    # Decode and validate the refresh token
    payload = decode_refresh_token(body.refresh_token)
    user_id = payload.get("sub")

    # Hash and look up
    token_hash = hash_token(body.refresh_token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if stored_token is not None:
        # Revoke the entire family
        now = datetime.now(timezone.utc)
        family_tokens = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_family_id == stored_token.token_family_id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
            .all()
        )
        for token in family_tokens:
            token.is_revoked = True
            token.revoked_at = now
            token.revoked_reason = "logout"

        # Audit log
        _create_audit_log(
            db=db,
            action_type=ActionType.USER_LOGOUT,
            user_id=int(user_id) if user_id else None,
            description=(
                f"User logged out. Token family '{stored_token.token_family_id}' revoked."
            ),
            ip_address=client["ip_address"],
            user_agent=client["user_agent"],
        )

    db.commit()
    return {"detail": "Successfully logged out."}


# ════════════════════════════════════════════════════════════════
# POST /auth/change-password
# ════════════════════════════════════════════════════════════════

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change the current user's password.

    Validates:
    1. Current password is correct.
    2. new_password == confirm_password.
    3. New password meets policy (PasswordValidator).
    4. New password is not in the last N password history entries.

    Side effects:
    - Updates password_hash on the User model.
    - Adds old hash to PasswordHistory.
    - Revokes ALL refresh tokens for this user.
    - Creates audit log entries.
    """
    client = get_client_info(request)

    # 1. Verify current password
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    # 2. Confirm passwords match
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password and confirmation password do not match.",
        )

    # 3. Validate against password policy
    validation = PasswordValidator.validate(body.new_password)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Password does not meet policy requirements.", "errors": validation.errors},
        )

    # 4. Check password history (last N entries)
    history_entries = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.user_id == current_user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(settings.PASSWORD_HISTORY_COUNT)
        .all()
    )
    for entry in history_entries:
        if verify_password(body.new_password, entry.password_hash):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Password has been used recently. "
                    f"Choose a password different from your last {settings.PASSWORD_HISTORY_COUNT}."
                ),
            )

    # ── All checks passed — perform the change ─────────────────
    old_hash = current_user.password_hash
    new_hash = hash_password(body.new_password)

    # Save old password to history
    history_entry = PasswordHistory(
        user_id=current_user.id,
        password_hash=old_hash,
    )
    db.add(history_entry)

    # Update user's password
    current_user.password_hash = new_hash
    current_user.password_changed_at = datetime.now(timezone.utc)
    current_user.password_changed_by = "self"
    current_user.must_change_password = False

    # Revoke ALL refresh tokens for this user
    now = datetime.now(timezone.utc)
    active_tokens = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
        .all()
    )
    for token in active_tokens:
        token.is_revoked = True
        token.revoked_at = now
        token.revoked_reason = "password_change"

    # Audit log
    _create_audit_log(
        db=db,
        action_type=ActionType.USER_UPDATED,
        user_id=current_user.id,
        description=f"User '{current_user.username}' changed their password.",
        resource_type="user",
        resource_id=current_user.id,
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )

    db.commit()

    return {"detail": "Password changed successfully. Please log in again."}


# ════════════════════════════════════════════════════════════════
# GET /auth/me
# ════════════════════════════════════════════════════════════════

@router.get("/me", response_model=UserInfo, status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the currently authenticated user's profile information.
    """
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        mfa_enabled=current_user.mfa_enabled,
    )


# ════════════════════════════════════════════════════════════════
# GET /auth/password-policy
# ════════════════════════════════════════════════════════════════

@router.get(
    "/password-policy",
    response_model=PasswordPolicyResponse,
    status_code=status.HTTP_200_OK,
)
def get_password_policy():
    """
    Return the password policy rules for frontend form validation.
    This endpoint is public (no authentication required).
    """
    return PasswordPolicyResponse(
        min_length=settings.PASSWORD_MIN_LENGTH,
        requires_uppercase=settings.PASSWORD_REQUIRE_UPPERCASE,
        requires_lowercase=settings.PASSWORD_REQUIRE_LOWERCASE,
        requires_digit=settings.PASSWORD_REQUIRE_DIGIT,
        requires_special=settings.PASSWORD_REQUIRE_SPECIAL,
        history_count=settings.PASSWORD_HISTORY_COUNT,
    )
