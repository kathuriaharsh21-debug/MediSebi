"""
MediSebi — Refresh Token Model
================================
Secure refresh token storage with family tracking and reuse detection.
Based on OWASP + OAuth 2.1 Token Rotation best practices.

SECURITY DESIGN:
────────────────
1. Tokens are NEVER stored in plaintext — only SHA-256 hashes.
2. Each token belongs to a "family" — linked refresh tokens from the same login session.
3. On each refresh, the old token is revoked and a new one is issued in the same family.
4. REUSE DETECTION: If a revoked token (reason="rotation") is used again, the ENTIRE
   family is revoked. This indicates the token was stolen and replayed by an attacker.
5. Token expiry + periodic pruning prevents table bloat.

FLOW:
─────
Client sends refresh token → Server hashes it → Looks up in DB
  ├─ Found, valid → Revoke old (reason="rotation") → Issue new in same family
  ├─ Already revoked (reason="rotation") → TOKEN THEFT DETECTED → Revoke family → Force re-login
  ├─ Already revoked (reason="logout") → Return 401 (normal logout)
  └─ Not found → Return 401 (invalid/expired)
"""

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from app.core.mixins import TimestampMixin


class RefreshToken(Base, TimestampMixin):
    """
    Single-use refresh tokens with rotation and family-based revocation.
    Tokens are hashed before storage — raw token values never touch the database.
    """
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        # Fast lookup: find active token by hash
        Index("ix_rt_token_hash", "token_hash", unique=True),
        # Revoke all tokens for a user at once
        Index("ix_rt_user", "user_id"),
        # Revoke entire family on theft detection
        Index("ix_rt_family", "token_family_id"),
        # Prune expired tokens efficiently
        Index("ix_rt_expires", "expires_at"),
        {
            "comment": (
                "Secure refresh token storage with OWASP-compliant rotation. "
                "SHA-256 hashed, family-tracked, reuse-detected."
            ),
        },
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ── Token Identity ──────────────────────────────────────
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 hash of the refresh token. Raw token is NEVER stored.",
    )
    token_family_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment=(
            "Groups related tokens from the same login session. "
            "If theft is detected, the ENTIRE family is revoked."
        ),
    )

    # ── Ownership ───────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner of this token",
    )

    # ── Lifecycle ───────────────────────────────────────────
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Whether this token has been revoked",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this token was revoked",
    )
    revoked_reason: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Reason for revocation: 'rotation', 'logout', 'password_change', 'theft_detected', 'admin_revoke'",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this token expires (absolute, not sliding)",
    )

    # ── Device & Location (Forensic) ────────────────────────
    device_fingerprint: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Hashed device identifier to detect unauthorized device reuse",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address from which the token was issued (IPv6 capable)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Client user-agent at token issuance time",
    )

    # ── Relationships ───────────────────────────────────────
    user = relationship(
        "User",
        back_populates="refresh_tokens",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} family={self.token_family_id[:16]}... "
            f"user_id={self.user_id} revoked={self.is_revoked}>"
        )
