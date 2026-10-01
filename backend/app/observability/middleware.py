"""
AURA Observability — Request Middleware.

Implements:
- Request ID / Correlation ID generation and propagation
- Structured access logging with latency
- Request context injection into structlog context vars
"""

from __future__ import annotations

import time

_bg_tasks = set()
import uuid
from datetime import UTC
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response
    from starlette.types import ASGIApp

logger = get_logger(__name__)

# HTTP header names for correlation
REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique request ID to every incoming request.

    - If the client provides X-Request-ID, it is used as-is (after validation).
    - Otherwise, a new UUIDv4 is generated.
    - The request ID is:
      1. Stored in request.state.request_id
      2. Injected into structlog context vars for all logs in this request
      3. Echoed back in the X-Request-ID response header
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Assign request ID (validate incoming to prevent header injection)
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = _sanitize_request_id(incoming) or str(uuid.uuid4())

        # Store on request state for handlers to access
        request.state.request_id = request_id

        # Bind to structlog context vars — all subsequent logs in this
        # async context will automatically include request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach correlation IDs to response headers
        response.headers[REQUEST_ID_HEADER] = request_id

        # Structured access log
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            client_host=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", ""),
        )

        # Push observability data to Redis if authenticated
        org_id = getattr(request.state, "organization_id", None)
        if org_id:
            import asyncio
            import json
            from datetime import datetime

            from app.security.rate_limit import get_redis_client

            metric = {
                "timestamp": datetime.now(UTC).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
                "tenant_id": org_id,
                "request_id": request_id,
            }

            async def push_metric(m):
                try:
                    redis = await get_redis_client()
                    key = f"observability:metrics:{org_id}"
                    await redis.lpush(key, json.dumps(m))
                    await redis.ltrim(key, 0, 9999)  # Keep last 10,000 requests
                except Exception:
                    pass

            task = asyncio.create_task(push_metric(metric))
            _bg_tasks.add(task)
            task.add_done_callback(_bg_tasks.discard)

        return response


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """
    Lightweight metrics middleware.

    Tracks per-request latency and status codes. Pushes aggregated counters
    to a structlog metric event so they can be scraped by any log aggregator.
    No external dependencies — metrics are emitted as structured log events.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
            )
            raise
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        # Emit a structured metrics event (picked up by log aggregators)
        logger.info(
            "request_metric",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
        )
        return response


def _sanitize_request_id(value: str) -> str:
    """
    Accept a client-provided request ID if it looks like a valid UUID or
    short alphanumeric string. Rejects anything suspicious.
    """
    if not value:
        return ""
    # Allow UUIDs and short identifiers (alphanumeric + hyphens, max 64 chars)
    import re

    if re.match(r"^[a-zA-Z0-9\-_]{1,64}$", value):
        return value
    return ""  # Reject — generate a new one instead
