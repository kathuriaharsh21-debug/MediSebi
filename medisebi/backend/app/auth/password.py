"""
MediSebi — Password Hashing Module
====================================
Provides bcrypt-based password hashing and verification.
Uses the bcrypt library directly for compatibility with bcrypt >= 4.1.
"""

import bcrypt
import re

from app.core.config import settings


def _extract_rounds(hashed_password: str) -> int:
    """Extract bcrypt rounds from an existing hash string."""
    match = re.match(r'\$2[aby]\$(\d{2})\$', hashed_password)
    if match:
        return int(match.group(1))
    return settings.BCRYPT_ROUNDS


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: Plaintext password string.

    Returns:
        Bcrypt hash string (e.g., $2b$12$...).
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Plaintext password string from user input.
        hashed_password: Stored bcrypt hash string.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


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
    existing_rounds = _extract_rounds(hashed_password)
    return existing_rounds < settings.BCRYPT_ROUNDS
