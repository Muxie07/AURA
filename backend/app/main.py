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

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import alembic.command
import alembic.config
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.database.base import close_database, initialize_database
from app.observability import (
    RequestIDMiddleware,
    RequestMetricsMiddleware,
    configure_logging,
    get_logger,
)


def upgrade_with_lock(cfg: alembic.config.Config) -> None:
    """Run Alembic upgrade in a worker thread; advisory lock lives in env.py."""
    alembic.command.upgrade(cfg, "head")


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging()
    logger = get_logger(__name__)

    logger.info("aura_starting", environment=settings.aura_env.value, debug=settings.aura_debug)

    if settings.aura_run_migrations_on_startup:
        logger.info("Running database migrations...")
        backend_root = Path(__file__).resolve().parent.parent
        ini_path = backend_root / "alembic.ini"
        alembic_cfg = alembic.config.Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(backend_root / "migrations"))
        await asyncio.to_thread(upgrade_with_lock, alembic_cfg)

    await initialize_database()

    from app.security.rate_limit import get_redis_client

    redis = await get_redis_client()
    try:
        await redis.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning(f"redis_connection_failed: {e}")

    from datetime import UTC, datetime, timedelta

    from app.database.base import get_session_factory
    from app.database.models import AgentRun, AgentRunStatus

    try:
        SessionFactory = get_session_factory()
        async with SessionFactory() as db:
            cutoff = datetime.now(UTC) - timedelta(
                seconds=settings.aura_agent_run_heartbeat_seconds * 3
            )
            await db.execute(
                sa.update(AgentRun)
                .where(
                    AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                    AgentRun.updated_at < cutoff,
                )
                .values(
                    status=AgentRunStatus.FAILED,
                    error_message="Worker lease expired/crashed",
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
            logger.info("stuck_run_recovery_complete")
    except Exception as e:
        logger.error("stuck_run_recovery_failed", error=str(e))

    from app.tools.registry import ToolRegistry
    from app.tools.mcp.client import MCPClientManager

    registry = ToolRegistry()
    app.state.tool_registry = registry
    mcp_manager = MCPClientManager()
    app.state.mcp_manager = mcp_manager

    yield

    logger.info("aura_shutting_down")
    grace = os.getenv("AURA_SHUTDOWN_GRACE_SECONDS", "5")
    logger.info(f"waiting {grace}s for in-flight requests")
    await asyncio.sleep(float(grace))
    await close_database()
    await app.state.mcp_manager.close()
    logger.info("aura_shutdown_complete")


class MaxSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


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

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.aura_trusted_hosts)
    app.add_middleware(MaxSizeMiddleware, max_bytes=settings.aura_max_request_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)

    if settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://your-production-domain.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID", "X-Correlation-ID"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Correlation-ID"],
        )

    # ---- Exception Handlers ---------------------------------------------
    register_exception_handlers(app)

    # ---- Routers --------------------------------------------------------
    from app.api.v1.router import api_v1_router

    @app.get("/ready", tags=["health"])
    async def readiness_check():
        """Detailed readiness probe (DB, Redis, Migrations)."""
        settings = get_settings()
        import sqlalchemy as sa
        from fastapi import HTTPException

        from app.database.base import get_session_factory
        from app.security.rate_limit import get_redis_client

        status = {"db": "ok", "redis": "ok"}
        ready = True
        try:
            SessionFactory = get_session_factory()
            async with SessionFactory() as db:
                await db.execute(sa.text("SELECT 1"))
        except Exception:
            status["db"] = "failed"
            ready = False

        try:
            redis = await get_redis_client()
            await redis.ping()
        except Exception:
            status["redis"] = "failed"
            ready = False

        if not ready:
            raise HTTPException(status_code=503, detail=status)
        try:
            # check MCP manager health
            if not getattr(app.state, "mcp_manager", None):
                status["mcp"] = "initializing"
            else:
                status["mcp"] = "ok" # Non-fatal
        except Exception:
            status["mcp"] = "unknown"
            
        return status

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
