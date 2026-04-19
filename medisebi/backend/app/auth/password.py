"""
MediSebi — Password Hashing Module
====================================
Provides bcrypt-based password hashing and verification.
Uses passlib with configurable bcrypt rounds from application settings.
"""

from passlib.context import CryptContext

from app.core.config import settings

# ── CryptContext Configuration ──────────────────────────────────
# bcrypt rounds are loaded from settings (default 12, ~0.34s per hash)
# This meets OWASP 2025 recommendations for work factor.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: Plaintext password string.

    Returns:
        Bcrypt hash string (e.g., $2b$12$...).
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Plaintext password string from user input.
        hashed_password: Stored bcrypt hash string.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a stored hash uses the current bcrypt round count.

    Called after successful login to opportunistically upgrade hashes
    when BCRYPT_ROUNDS is increased across the organization.

    Args:
        hashed_password: Stored bcrypt hash string.

    Returns:
        True if the hash should be rehashed with current settings.
    """
    return pwd_context.needs_update(hashed_password)
