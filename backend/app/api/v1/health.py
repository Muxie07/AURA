"""
AURA API v1 — Health Check Endpoint.

Provides:
- GET /health — Simple liveness probe
- GET /api/v1/health — Detailed readiness probe with dependency checks
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DatabaseDep, SettingsDep
from app.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


class ComponentHealth(BaseModel):
    """Health status of a single dependency component."""

    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Full health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    version: str
    environment: str
    components: dict[str, ComponentHealth]


@router.get(
    "/health",
    response_model=HealthResponse,
    response_class=ORJSONResponse,
    summary="Detailed health check",
    description=(
        "Performs readiness checks against all application dependencies. "
        "Returns 200 if healthy, 503 if any critical dependency is unhealthy."
    ),
)
async def health_check(
    settings: SettingsDep,
    db: DatabaseDep,
) -> ORJSONResponse:
    """
    Detailed readiness probe.

    Checks:
    - Database connectivity and latency
    - Application configuration validity

    Returns HTTP 200 if all critical components are healthy.
    Returns HTTP 503 if any critical component is unhealthy.
    """
    components: dict[str, ComponentHealth] = {}
    overall_status: Literal["healthy", "degraded", "unhealthy"] = "healthy"

    # --- Database check ---------------------------------------------------
    db_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        components["database"] = ComponentHealth(
            status="healthy",
            latency_ms=db_latency,
        )
    except Exception as exc:
        logger.error("health_check_db_failed", error=str(exc))
        components["database"] = ComponentHealth(
            status="unhealthy",
            detail="Database connection failed.",
        )
        overall_status = "unhealthy"

    # Build response
    response_body = HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version="0.1.0",
        environment=settings.aura_env.value,
        components=components,
    )

    status_code = 200 if overall_status == "healthy" else 503
    return ORJSONResponse(content=response_body.model_dump(mode="json"), status_code=status_code)


# ---------------------------------------------------------------------------
# Simple liveness endpoint (no dependencies — ultra-fast Kubernetes probe)
# ---------------------------------------------------------------------------
@router.get(
    "/ping",
    include_in_schema=False,
    summary="Liveness ping",
)
async def ping() -> dict[str, str]:
    """Ultra-lightweight liveness probe. Does not check dependencies."""
    return {"status": "ok"}
