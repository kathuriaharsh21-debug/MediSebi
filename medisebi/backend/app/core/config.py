"""
MediSebi — Application Configuration
=====================================
Centralized configuration using Pydantic BaseSettings.
Loads from environment variables with sensible defaults for development.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All secrets MUST be set via environment variables in production.
    """

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "MediSebi"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-Driven Healthcare Supply Intelligence & Redistribution Platform"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-DO-NOT-USE-IN-PROD",
        description="JWT signing key. MUST be overridden in production via env var."
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30       # 30 minutes (short-lived)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7 days with rotation
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12                     # OWASP 2025 recommendation (~0.34s)

    # ── Password Policy ─────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 12               # HIPAA / NIST minimum
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_HISTORY_COUNT: int = 12             # Prevent reuse of last 12
    PASSWORD_MAX_AGE_DAYS: int = 90             # Force reset every 90 days
    ACCOUNT_LOCKOUT_THRESHOLD: int = 5          # Lock after 5 failed attempts
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30  # Auto-unlock after 30 min

    # ── MFA / 2FA ───────────────────────────────────────────
    MFA_ISSUER_NAME: str = "MediSebi"
    MFA_TOTP_DIGITS: int = 6
    MFA_TOTP_PERIOD: int = 30                   # Seconds per TOTP code

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite:///./medisebi_dev.db",
        description="Database connection string. Defaults to SQLite for development."
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False  # Set True for SQL query logging

    # ── OpenWeather API ──────────────────────────────────────
    OPENWEATHER_API_KEY: Optional[str] = None
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # ── ML / Forecasting ─────────────────────────────────────
    FORECAST_HORIZON_DAYS: int = 7
    EXPIRY_WARNING_DAYS: int = 30

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_MINUTES: int = 15

    # ── Notification Settings ───────────────────────────────
    NOTIFICATION_DEFAULT_TTL_DAYS: int = 30     # Auto-prune after 30 days
    NOTIFICATION_MAX_PER_USER: int = 500         # Cap stored notifications per user
    NOTIFICATION_CRITICAL_TTL_DAYS: int = 90    # Critical alerts last longer

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton instance
settings = Settings()
