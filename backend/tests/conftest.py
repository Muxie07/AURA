"""
AURA Test Suite — Pytest Configuration & Fixtures.

Provides:
- In-memory SQLite (via aiosqlite) for fast unit tests
- Full PostgreSQL test database for integration tests
- Async test client with proper lifespan handling
- Factory fixtures for common model creation
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Environment, Settings, get_settings
from app.database.base import Base, get_db_session
from app.database.models import (
    Conversation,
    ConversationStatus,
    Organization,
    User,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI

# =============================================================================
# Test Settings Override
# =============================================================================

TEST_SETTINGS = Settings(
    aura_env=Environment.DEVELOPMENT,
    aura_debug=True,
    aura_secret_key="test-secret-key-at-least-32-characters-long",  # type: ignore[arg-type]
    postgres_host="localhost",
    postgres_db="aura_test",
    postgres_user="aura",
    postgres_password="aura-dev-password",  # type: ignore[arg-type]
    aura_log_format="text",  # type: ignore[arg-type]
    aura_log_level="WARNING",  # Quiet during tests
)


# =============================================================================
# In-Memory SQLite Engine for fast unit tests
# =============================================================================

@pytest.fixture(scope="session")
def sqlite_engine():
    """
    Session-scoped async SQLite engine for unit tests.

    SQLite is used to avoid requiring a real PostgreSQL instance for
    unit tests. Integration tests requiring PostgreSQL-specific features
    (JSONB, pgvector, etc.) should use the postgres_engine fixture instead.
    """
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    return engine


@pytest_asyncio.fixture
async def create_tables(sqlite_engine):
    """Create all tables in the in-memory SQLite database."""
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(sqlite_engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a clean async database session for each test.
    """
    factory = async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    import app.database.base
    app.database.base._session_factory = factory
    async with factory() as session, session.begin():
        yield session
        await session.rollback()
    app.database.base._session_factory = None


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> FastAPI:
    """
    Returns a configured FastAPI test application with mocked dependencies.

    Database sessions are provided by the test fixture rather than the
    real connection pool.
    """
    # Patch settings to use test configuration
    get_settings.cache_clear()

    from app.main import create_app

    test_app = create_app()

    def override_get_settings():
        return TEST_SETTINGS
    test_app.dependency_overrides[get_settings] = override_get_settings



    # Override the database dependency
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_get_db

    # Patch get_session_factory globally for tests
    import app.database.base as db_base
    from unittest.mock import MagicMock
    mock_factory = MagicMock()
    mock_factory.return_value = db_session
    db_base.get_session_factory = lambda: lambda: db_session





    return test_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    from jose import jwt
    token = jwt.encode(
        {"sub": str(_DEFAULT_USER_ID), "org_id": str(_DEFAULT_ORG_ID), "exp": 9999999999},
        TEST_SETTINGS.aura_secret_key.get_secret_value(),
        algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


# =============================================================================
# Model Factories
# =============================================================================

_DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest_asyncio.fixture
async def organization(db_session: AsyncSession) -> Organization:
    """Create and persist a test organization."""
    org = Organization(
        id=_DEFAULT_ORG_ID,
        name="Test Organization",
        slug="test-org",
        is_active=True,
        settings={},
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def user(db_session: AsyncSession, organization: Organization) -> User:
    """Create and persist a test user."""
    u = User(
        id=_DEFAULT_USER_ID,
        organization_id=organization.id,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        metadata_={},
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def conversation(
    db_session: AsyncSession,
    organization: Organization,
    user: User,
) -> Conversation:
    """Create and persist a test conversation."""
    conv = Conversation(
        organization_id=organization.id,
        user_id=user.id,
        title="Test Conversation",
        status=ConversationStatus.ACTIVE,
        metadata_={},
    )
    db_session.add(conv)
    await db_session.flush()
    return conv


@pytest.fixture(autouse=True)
async def cleanup_redis():
    yield
    import app.security.rate_limit as rl
    if rl._redis_client is not None:
        try:
            await rl._redis_client.aclose()
        except:
            pass
        rl._redis_client = None
