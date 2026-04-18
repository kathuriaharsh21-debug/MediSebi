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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12

    # ── PostgreSQL Database ──────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://medisebi_user:medisebi_pass@localhost:5432/medisebi_db",
        description="PostgreSQL connection string."
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton instance
settings = Settings()
