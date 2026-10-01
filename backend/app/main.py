"""
AURA Backend — Application Entry Point.

Creates and configures the FastAPI application using the lifespan pattern
for clean startup/shutdown resource management.

Architecture:
- App factory pattern (create_app) for testability
- Lifespan context manager for resource lifecycle
- Layered middleware (outermost = first to execute)
- Centralized exception handler registration
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.database.base import close_database, initialize_database
from app.observability import RequestIDMiddleware, configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown of:
    - Logging
    - Database connection pool
    - (Future phases: Redis, background workers, ML model warmup)
    """
    # ---- Startup ---------------------------------------------------------
    settings = get_settings()

    # Configure logging first so all subsequent startup logs are structured
    configure_logging()
    logger = get_logger(__name__)

    logger.info(
        "aura_starting",
        environment=settings.aura_env.value,
        debug=settings.aura_debug,
        version="0.1.0",
    )

    # Run migrations in a worker thread because Alembic's async
    # migration environment manages its own event loop.
    import asyncio

    import alembic.command
    import alembic.config
    logger.info("Running database migrations...")
    alembic_cfg = alembic.config.Config("alembic.ini")
    await asyncio.to_thread(alembic.command.upgrade, alembic_cfg, "head")

    await initialize_database()

    # Recovery: Mark stuck agent runs as FAILED
    import sqlalchemy as sa

    from app.database.base import get_session_factory
    from app.database.models import AgentRun, AgentRunStatus
    try:
        SessionFactory = get_session_factory()
        async with SessionFactory() as db:
            await db.execute(
                sa.update(AgentRun)
                .where(AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]))
                .values(
                    status=AgentRunStatus.FAILED,
                    error_message="Server crashed during execution",
                    completed_at=sa.func.now()
                )
            )
            await db.commit()
            logger.info("Recovered stuck agent runs.")
    except Exception as exc:
        logger.warning("Failed to recover stuck agent runs.", error=str(exc))

    # Check Redis connectivity
    import redis.asyncio as aioredis
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping() # type: ignore[misc]
        await redis_client.aclose()
    except Exception as exc:
        logger.error("Redis connection failed.", error=str(exc))
        raise RuntimeError(f"Failed to connect to Redis: {exc}") from exc

    logger.info("aura_ready", api_base_url=str(settings.aura_api_base_url))

    # ---- Hand control to the application --------------------------------
    yield

    # ---- Shutdown --------------------------------------------------------
    logger.info("aura_shutting_down")
    await close_database()
    logger.info("aura_stopped")


def create_app() -> FastAPI:
    """
    Application factory.

    Returns a fully configured FastAPI instance.
    Call this from uvicorn or tests.
    """
    settings = get_settings()

    app = FastAPI(
        title="AURA — Autonomous AI Business Operations Engineer",
        description=(
            "Production-quality AI agent platform for business operations automation. "
            "Handles quotation generation, customer lookup, document analysis, and more "
            "through a controlled, auditable, human-in-the-loop agent architecture."
        ),
        version="0.1.0",
        # Use ORJSONResponse for performance
        default_response_class=ORJSONResponse,
        # Docs available in non-production environments
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
        # Contact info for OpenAPI spec
        contact={
            "name": "AURA Engineering",
            "url": "https://github.com/your-org/aura",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # ---- Middleware (order matters: last added = outermost wrapper) ------

    # CORS — must be before RequestID so preflight requests get correct headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.aura_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # Request ID — outermost so all logs include the request ID
    app.add_middleware(RequestIDMiddleware)

    # ---- Exception Handlers ---------------------------------------------
    register_exception_handlers(app)

    # ---- Routers --------------------------------------------------------
    from app.api.v1.router import api_v1_router

    app.include_router(api_v1_router)
    
    from app.tools.mcp.routes import asgi_sse
    app.mount("/api/v1/mcp", asgi_sse)

    # Root liveness probe (no auth, no DB) — used by load balancers
    @app.get("/health", include_in_schema=False, tags=["Health"])
    async def root_health() -> ORJSONResponse:
        """Root-level liveness probe. Does not check dependencies."""
        return ORJSONResponse({"status": "ok", "version": "0.1.0"})

    return app


# Entry point for `uvicorn app.main:app`
app = create_app()
