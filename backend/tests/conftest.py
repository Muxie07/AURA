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

from app.config.settings import Environment, ModelProvider, Settings, get_settings
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

import os

os.environ["AURA_SECRET_KEY"] = "test-secret-key-at-least-32-characters-long"

TEST_SETTINGS = Settings(
    aura_env=Environment.DEVELOPMENT,
    aura_debug=True,
    aura_secret_key="test-secret-key-at-least-32-characters-long",  # type: ignore[arg-type]
    postgres_host=os.environ.get("POSTGRES_HOST", "postgres"),
    postgres_db="aura_test",
    postgres_user=os.environ.get("POSTGRES_USER", "aura"),
    postgres_password=os.environ.get("POSTGRES_PASSWORD", "aura_password"),  # type: ignore[arg-type]
    redis_host=os.environ.get("REDIS_HOST", "redis"),
    redis_port=int(os.environ.get("REDIS_PORT", "6379")),
    aura_log_format="text",  # type: ignore[arg-type]
    aura_log_level="WARNING",  # Quiet during tests
    primary_llm_provider=ModelProvider.MOCK,
)


# =============================================================================
# In-Memory SQLite Engine for fast unit tests
# =============================================================================


@pytest_asyncio.fixture(scope="session")
async def postgres_engine():
    engine = create_async_engine(
        TEST_SETTINGS.database_url,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def create_tables(postgres_engine):
    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(postgres_engine, create_tables):
    factory = async_sessionmaker(
        bind=postgres_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    import contextlib

    import app.database.base
    class FakeFactory:
        def __call__(self):
            @contextlib.asynccontextmanager
            async def _cm():
                yield session
            return _cm()
    app.database.base._session_factory = FakeFactory()


    async with factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            if session.in_transaction():
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
    def mock_get_settings():
        env_provider = os.environ.get("PRIMARY_LLM_PROVIDER", os.environ.get("AURA_MODEL_PROVIDER"))
        if env_provider:
            try:
                TEST_SETTINGS.primary_llm_provider = ModelProvider(env_provider.lower())
            except ValueError:
                TEST_SETTINGS.primary_llm_provider = ModelProvider.MOCK
        else:
            TEST_SETTINGS.primary_llm_provider = ModelProvider.MOCK
        return TEST_SETTINGS

    mock_get_settings.cache_clear = lambda: None

    import app.config.settings
    import app.security.rate_limit
    import app.tools.mcp.routes

    app.config.settings.get_settings = mock_get_settings
    app.tools.mcp.routes.get_settings = mock_get_settings
    app.security.rate_limit.get_settings = mock_get_settings

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
    from unittest.mock import MagicMock

    import app.database.base as db_base

    mock_factory = MagicMock()
    mock_factory.return_value = db_session
    db_base.get_session_factory = lambda: lambda: db_session

    return test_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    from jose import jwt

    token = jwt.encode(
        {"sub": str(_DEFAULT_USER_ID), "org_id": str(_DEFAULT_ORG_ID), "exp": 9999999999, "iss": "aura", "aud": "aura"},
        TEST_SETTINGS.aura_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac




# =============================================================================
# Model Factories
# =============================================================================

def get_org_id(): return uuid.uuid4()
_DEFAULT_ORG_ID = get_org_id()
def get_user_id(): return uuid.uuid4()
_DEFAULT_USER_ID = get_user_id()


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
    org = await db_session.merge(org)
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

        metadata_={},
    )
    u = await db_session.merge(u)
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
    conv = await db_session.merge(conv)
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
