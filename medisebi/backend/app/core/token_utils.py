"""
MediSebi — Token Hashing & JWT Utility
========================================
Secure utility for hashing/verifying tokens and decoding JWTs.
Refresh tokens are NEVER stored in plaintext — only SHA-256 hashes.
"""

import hashlib
import secrets
import uuid
from datetime import datetime

from jose import jwt, JWTError


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.
    Returns the payload dict if valid, None if invalid/expired.
    """
    from app.core.config import settings

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def create_access_token(data: dict, expires_delta_minutes: int | None = None) -> str:
    """
    Create a JWT access token.
    """
    from app.core.config import settings
    from datetime import timedelta

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=expires_delta_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def hash_token(token: str) -> str:
    """
    Hash a refresh token using SHA-256.
    Used for storing tokens in the database — raw tokens are never persisted.

    Args:
        token: The raw JWT refresh token string.

    Returns:
        64-character hexadecimal SHA-256 hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    """
    Verify a raw token against a stored hash.
    Used during refresh token validation.

    Args:
        raw_token: The raw JWT refresh token from the client.
        stored_hash: The SHA-256 hash stored in the refresh_tokens table.

    Returns:
        True if the hash matches, False otherwise.
    """
    return hash_token(raw_token) == stored_hash


def generate_token_family_id() -> str:
    """
    Generate a unique token family ID.
    All rotated tokens from the same login session share this family ID.
    If token theft is detected, the entire family is revoked.

    Returns:
        16-character hexadecimal string.
    """
    return uuid.uuid4().hex[:16]


def generate_device_fingerprint(user_agent: str, ip_address: str | None) -> str:
    """
    Generate a deterministic device fingerprint from user-agent and IP.
    Used to detect suspicious login patterns (new device / location).

    Args:
        user_agent: Client's User-Agent header.
        ip_address: Client's IP address.

    Returns:
        64-character SHA-256 hash of the combined inputs.
    """
    raw = f"{user_agent}|{ip_address or 'unknown'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    Used for password reset links, email verification, etc.

    Args:
        nbytes: Number of random bytes (default 32 = 256 bits of entropy).

    Returns:
        URL-safe base64 encoded string.
    """
    return secrets.token_urlsafe(nbytes)
