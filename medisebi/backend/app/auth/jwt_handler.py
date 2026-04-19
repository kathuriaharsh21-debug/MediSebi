"""
MediSebi — JWT Token Handler
=============================
Handles creation, decoding, and validation of JSON Web Tokens.
- Access tokens are short-lived (30 min) for API authentication.
- Refresh tokens are longer-lived (7 days) and support rotation.
"""

from datetime import datetime, timedelta, timezone
import uuid

from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload to encode. Must include 'sub' (user_id).
        expires_delta: Custom expiration time. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode.update(
        {
            "iat": now,
            "exp": expire,
            "type": "access",
            "jti": uuid.uuid4().hex,
        }
    )

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """
    Create a signed JWT refresh token.

    The refresh token includes:
    - jti: Unique token ID (UUID) for tracking and revocation.
    - sub: Set to the user_id by the caller (not included here; caller must add it).
    - exp: Expiration based on REFRESH_TOKEN_EXPIRE_DAYS.
    - type: "refresh" to distinguish from access tokens.

    Returns:
        Tuple of (raw_token, token_hash).
        The raw_token is sent to the client.
        The token_hash (SHA-256) is stored in the database.
        The caller is responsible for adding 'sub' before encoding if needed,
        but typically the payload is built here.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = uuid.uuid4().hex

    payload = {
        "jti": jti,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }

    raw_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Hash for database storage — raw token never touches DB
    from app.core.token_utils import hash_token

    token_hash = hash_token(raw_token)

    return raw_token, token_hash


def create_refresh_token_for_user(user_id: int) -> tuple[str, str]:
    """
    Create a refresh token for a specific user.

    Args:
        user_id: The user's database ID, embedded in the token as 'sub'.

    Returns:
        Tuple of (raw_token, token_hash).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = uuid.uuid4().hex

    payload = {
        "jti": jti,
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }

    raw_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    from app.core.token_utils import hash_token

    token_hash = hash_token(raw_token)

    return raw_token, token_hash


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: Encoded JWT access token string.

    Returns:
        Decoded token payload dict.

    Raises:
        HTTPException: If token is expired, invalid, or not an access token.
    """
    from fastapi import HTTPException, status

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure this is an access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def decode_refresh_token(raw_token: str) -> dict:
    """
    Decode and validate a raw JWT refresh token.

    Args:
        raw_token: Raw JWT refresh token string from the client.

    Returns:
        Decoded token payload dict.

    Raises:
        HTTPException: If token is expired, invalid, or not a refresh token.
    """
    from fastapi import HTTPException, status

    try:
        payload = jwt.decode(
            raw_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Ensure this is a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected refresh token.",
        )

    return payload
