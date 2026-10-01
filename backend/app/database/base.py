"""
AURA Database — SQLAlchemy Async Engine & Session Management.

Provides:
- Async engine with connection pooling
- Session factory
- Dependency injection helper for FastAPI
- Base model class with common columns
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config.settings import get_settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Naming Convention
# Consistent constraint naming prevents Alembic from generating generic names
# =============================================================================
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base with shared metadata and naming convention.

    All ORM models in AURA should inherit from this class.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # -------------------------------------------------------------------------
    # Common timestamp columns — inherited by all models
    # -------------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last-update timestamp (UTC).",
    )

    def __repr__(self) -> str:
        """Generic repr showing class name and primary key values."""
        pk_cols = [c.name for c in self.__table__.primary_key]
        pk_vals = {col: getattr(self, col, "?") for col in pk_cols}
        pk_str = ", ".join(f"{k}={v!r}" for k, v in pk_vals.items())
        return f"<{self.__class__.__name__}({pk_str})>"


# =============================================================================
# Engine & Session Factory
# These are module-level singletons initialized during app startup.
# =============================================================================
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine() -> AsyncEngine:
    """Create and return the async SQLAlchemy engine."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.aura_db_pool_size,
        max_overflow=settings.aura_db_max_overflow,
        pool_timeout=settings.aura_db_pool_timeout,
        pool_pre_ping=True,  # Validate connections before use
        echo=settings.aura_debug,  # Log SQL in debug mode
        # JSON serialization through orjson for performance
        json_serializer=_json_serializer,
        json_deserializer=_json_deserializer,
    )
    return engine


def _json_serializer(obj: Any) -> str:
    """Use orjson for fast JSON serialization in SQLAlchemy."""
    import orjson

    return orjson.dumps(obj).decode()


def _json_deserializer(data: str) -> Any:
    """Use orjson for fast JSON deserialization in SQLAlchemy."""
    import orjson

    return orjson.loads(data)


def get_engine() -> AsyncEngine:
    """Return the module-level engine, raising if not initialized."""
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. "
            "Call initialize_database() during application startup."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level session factory, raising if not initialized."""
    if _session_factory is None:
        raise RuntimeError(
            "Session factory not initialized. "
            "Call initialize_database() during application startup."
        )
    return _session_factory


async def initialize_database() -> None:
    """
    Initialize the database engine and session factory.

    Call this once during application lifespan startup.
    """
    global _engine, _session_factory

    logger.info("Initializing database connection pool.")
    _engine = create_engine()
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy-load errors after commit
        autoflush=False,
        autocommit=False,
    )

    # Verify connectivity
    try:
        async with _engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as exc:
        logger.error("Database connection failed.", error=str(exc))
        raise


async def close_database() -> None:
    """
    Dispose the database connection pool.

    Call this during application lifespan shutdown.
    """
    global _engine, _session_factory

    if _engine is not None:
        logger.info("Closing database connection pool.")
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    The session is committed on success and rolled back on exception.
    Always yields a fresh session from the pool.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
