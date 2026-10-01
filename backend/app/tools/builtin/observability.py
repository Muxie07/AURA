"""
AURA Observability Tool — read-only API latency & metrics retrieval.

Reads real request metrics stored in Redis by the RequestIDMiddleware.
Enforces strict tenant isolation: data is keyed by organization_id.
"""

from __future__ import annotations

import json
from typing import Any

from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

_OBSERVABILITY_DEF = ToolDefinition(
    name="observability.get_api_latency",
    description=(
        "Retrieve real API latency metrics, request counts, error rates, and"
        " slowest-endpoint statistics from the live observability datastore."
        " Use this tool when the user asks about API performance, latency,"
        " response times, errors, slow endpoints, or system health."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "time_range": {
                "type": "string",
                "description": (
                    "Time range for the metrics, e.g. '24h', '1h', 'recent'."
                    " Currently used as a label; data is the latest N requests."
                ),
            },
            "endpoint_prefix": {
                "type": "string",
                "description": (
                    "Optional URL path prefix to filter, e.g. '/api/v1'."
                    " Omit to include all endpoints."
                ),
            },
        },
        "required": ["time_range"],
    },
    risk_level=RiskLevel.READ,
    requires_approval=False,
    timeout_seconds=10,
    organization_scoped=True,
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def _observability_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """
    Read latency metrics from Redis for the requesting tenant.

    Metrics are stored as a Redis List keyed:
        observability:metrics:<organization_id>

    Each element is a JSON object written by RequestIDMiddleware.
    """
    from app.security.rate_limit import get_redis_client

    org_id = str(context.organization_id)
    redis = await get_redis_client()
    key = f"observability:metrics:{org_id}"

    # Fetch up to 2 000 recent records (newest first from LPUSH)
    raw_metrics = await redis.lrange(key, 0, 1999)

    if not raw_metrics:
        return {
            "message": (
                "No historical latency data is available yet. "
                "AURA's observability instrumentation is now connected, "
                "so new API requests will be recorded for analysis."
            ),
            "request_count": 0,
            "time_range": arguments.get("time_range", "recent"),
        }

    prefix: str = arguments.get("endpoint_prefix") or ""

    latencies: list[float] = []
    error_count = 0
    endpoint_times: dict[str, list[float]] = {}
    status_counts: dict[int, int] = {}

    for raw in raw_metrics:
        try:
            # raw may be bytes or str depending on redis-py version
            metric = json.loads(raw if isinstance(raw, str) else raw.decode())
        except Exception:
            continue

        path: str = metric.get("path", "")
        if prefix and not path.startswith(prefix):
            continue

        dur: float = float(metric.get("duration_ms", 0))
        status: int = int(metric.get("status_code", 200))

        latencies.append(dur)
        status_counts[status] = status_counts.get(status, 0) + 1
        if status >= 400:
            error_count += 1

        endpoint_times.setdefault(path, []).append(dur)

    if not latencies:
        return {
            "message": "No matching observability data found for the given filters.",
            "request_count": 0,
            "time_range": arguments.get("time_range", "recent"),
        }

    latencies_sorted = sorted(latencies)
    count = len(latencies_sorted)

    def _percentile(pct: float) -> float:
        """Linear interpolation percentile."""
        k = (count - 1) * pct
        lo = int(k)
        hi = min(lo + 1, count - 1)
        return latencies_sorted[lo] + (k - lo) * (latencies_sorted[hi] - latencies_sorted[lo])

    # Slowest endpoints (by average latency, top 5)
    slowest = sorted(
        [
            {
                "path": path,
                "avg_ms": round(sum(times) / len(times), 2),
                "calls": len(times),
                "p95_ms": round(
                    sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0], 2
                ),
            }
            for path, times in endpoint_times.items()
        ],
        key=lambda x: x["avg_ms"],
        reverse=True,
    )[:5]

    return {
        "time_range": arguments.get("time_range", "recent"),
        "request_count": count,
        "average_latency_ms": round(sum(latencies) / count, 2),
        "p50_latency_ms": round(_percentile(0.50), 2),
        "p95_latency_ms": round(_percentile(0.95), 2),
        "p99_latency_ms": round(_percentile(0.99), 2),
        "error_rate_percent": round((error_count / count) * 100, 2),
        "error_count": error_count,
        "status_distribution": status_counts,
        "slowest_endpoints": slowest,
    }


# ---------------------------------------------------------------------------
# Executor instance (registered at startup)
# ---------------------------------------------------------------------------

observability_get_api_latency_tool = InternalToolExecutor(
    _OBSERVABILITY_DEF, _observability_handler
)
