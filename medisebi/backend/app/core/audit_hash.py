"""
MediSebi — Audit Hash Utility
================================
Computes SHA-256 hashes for audit log integrity verification.
This function MUST be called BEFORE inserting an AuditLog record.
The hash covers all critical fields to make tampering detectable.
"""

import hashlib
import json
from typing import Any


def compute_audit_hash(
    action_type: str,
    user_id: int | None,
    timestamp: str,
    details: str | None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    secret_pepper: str = "medisebi_audit_pepper_2024",
) -> str:
    """
    Compute a SHA-256 hash for an audit log entry.

    The hash is computed over a canonical JSON string of all critical fields,
    plus a server-side "pepper" that is NOT stored in the database.
    This makes it impossible to forge a valid hash without knowing the pepper.

    Args:
        action_type: The action performed (e.g., 'stock_added').
        user_id: ID of the user who performed the action.
        timestamp: ISO-8601 timestamp string.
        details: JSON payload of the transaction details.
        resource_type: Type of resource affected.
        resource_id: ID of the resource affected.
        secret_pepper: Server-side secret (NEVER expose this value).

    Returns:
        64-character hexadecimal SHA-256 hash string.

    Example:
        >>> hash_val = compute_audit_hash(
        ...     action_type="stock_added",
        ...     user_id=1,
        ...     timestamp="2024-01-15T10:30:00Z",
        ...     details='{"med_id": 5, "quantity": 100}',
        ... )
        >>> len(hash_val)
        64
    """
    payload = {
        "action_type": action_type,
        "user_id": user_id,
        "timestamp": timestamp,
        "details": details or "",
        "resource_type": resource_type,
        "resource_id": resource_id,
    }

    # Sort keys for deterministic hashing
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Include pepper to prevent hash forgery even if DB is compromised
    salted_input = f"{canonical}|{secret_pepper}"

    return hashlib.sha256(salted_input.encode("utf-8")).hexdigest()


def verify_audit_hash(
    stored_hash: str,
    action_type: str,
    user_id: int | None,
    timestamp: str,
    details: str | None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    secret_pepper: str = "medisebi_audit_pepper_2024",
) -> bool:
    """
    Verify an audit log entry's SHA-256 hash against its stored value.

    Used during compliance audits to detect tampering.
    Returns True if the hash matches, False if any field has been modified.

    Args:
        stored_hash: The SHA-256 hash stored in the audit_logs table.
        All other args: Same as compute_audit_hash().

    Returns:
        True if integrity is intact, False if tampering detected.
    """
    computed = compute_audit_hash(
        action_type=action_type,
        user_id=user_id,
        timestamp=timestamp,
        details=details,
        resource_type=resource_type,
        resource_id=resource_id,
        secret_pepper=secret_pepper,
    )
    return computed == stored_hash
