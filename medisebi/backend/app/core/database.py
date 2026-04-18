"""
MediSebi — Database Session Management
========================================
SQLAlchemy engine and session factory with lazy initialization.
The engine is created on first access to avoid import-time DB connection errors.
"""

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Generator

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base class.
    All ORM models inherit from this class.
    """
    pass


# ── Lazy Engine Initialization ──────────────────────────────────
# Using a module-level factory pattern to defer connection until needed.
_engine = None


def get_engine():
    """
    Lazy-initialized database engine.
    Created on first call to avoid import-time connection errors
    (useful during migrations, testing, and schema validation).

    Automatically detects SQLite URLs and applies SQLite-compatible settings:
    - check_same_thread=False for multi-threaded access
    - StaticPool instead of QueuePool (SQLite doesn't support connection pooling)
    """
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL

        # Validate the URL is parseable; fall back to local SQLite if not
        try:
            from sqlalchemy import make_url
            make_url(db_url)
        except Exception:
            fallback = "sqlite:///./medisebi_dev.db"
            logger.warning(
                "DATABASE_URL '%s' is not a valid SQLAlchemy URL — falling back to %s",
                db_url, fallback,
            )
            db_url = fallback

        if db_url.startswith("sqlite"):
            # SQLite-compatible settings
            connect_args = {"check_same_thread": False}
            _engine = create_engine(
                db_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=settings.DATABASE_ECHO,
            )
        else:
            # PostgreSQL / other databases with connection pooling
            _engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
                echo=settings.DATABASE_ECHO,
            )
    return _engine


# ── Session Factory ─────────────────────────────────────────────
def get_session_factory():
    """
    Returns a sessionmaker bound to the current engine.
    Safe to call multiple times — returns the same factory.
    """
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator:
    """
    FastAPI dependency that yields a database session.
    Ensures the session is always properly closed after use.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
