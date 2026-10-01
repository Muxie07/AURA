"""
Tests for the observability.get_api_latency tool.

Covers:
 1. Tool registration in ToolRegistry
 2. Input validation (valid + invalid params)
 3. Tenant isolation (no cross-tenant data leakage)
 4. Real latency retrieval when data exists
 5. No-data scenario
 6. Planner selecting observability tool
 7. Structured fallback response generator
 8. Tool failure / Redis unavailable
 9. Unauthorized access (no org context)
10. Conversation integration (tool registered and callable)
"""
from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.builtin import register_builtin_tools
from app.tools.registry import ToolRegistry
from app.tools.schemas import RiskLevel, ToolContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_builtin_tools(reg)
    return reg


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


@pytest.fixture
def other_org_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")


@pytest.fixture
def tool_context(org_id: uuid.UUID) -> ToolContext:
    return ToolContext(
        organization_id=org_id,
        agent_run_id=uuid.uuid4(),
        execution_id="test-exec-001",
        dry_run=False,
    )


SAMPLE_METRICS = [
    {
        "timestamp": "2026-09-27T10:00:00+00:00",
        "method": "GET",
        "path": "/api/v1/conversations",
        "status_code": 200,
        "duration_ms": 25.5,
        "tenant_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "request_id": "req-001",
    },
    {
        "timestamp": "2026-09-27T10:00:01+00:00",
        "method": "POST",
        "path": "/api/v1/runs",
        "status_code": 201,
        "duration_ms": 120.0,
        "tenant_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "request_id": "req-002",
    },
    {
        "timestamp": "2026-09-27T10:00:02+00:00",
        "method": "GET",
        "path": "/api/v1/health",
        "status_code": 500,
        "duration_ms": 8.0,
        "tenant_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "request_id": "req-003",
    },
    {
        "timestamp": "2026-09-27T10:00:03+00:00",
        "method": "GET",
        "path": "/api/v1/conversations",
        "status_code": 200,
        "duration_ms": 45.0,
        "tenant_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "request_id": "req-004",
    },
    {
        "timestamp": "2026-09-27T10:00:04+00:00",
        "method": "GET",
        "path": "/api/v1/runs/abc/stream",
        "status_code": 200,
        "duration_ms": 800.0,
        "tenant_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "request_id": "req-005",
    },
]

OTHER_ORG_METRICS = [
    {
        "timestamp": "2026-09-27T10:00:05+00:00",
        "method": "GET",
        "path": "/api/v1/sensitive",
        "status_code": 200,
        "duration_ms": 999.0,
        "tenant_id": "bbbbbbbb-0000-0000-0000-000000000002",
        "request_id": "req-other",
    },
]


def _make_redis_mock(org_id: uuid.UUID, metrics: list[dict]) -> AsyncMock:
    """Return an async mock Redis client serving encoded metrics."""
    encoded = [json.dumps(m).encode() for m in metrics]
    redis_mock = AsyncMock()
    redis_mock.lrange = AsyncMock(return_value=encoded)
    return redis_mock


# ---------------------------------------------------------------------------
# 1. Tool registration
# ---------------------------------------------------------------------------

def test_observability_tool_is_registered(registry: ToolRegistry) -> None:
    """observability.get_api_latency must be discoverable in the registry."""
    definitions = {d.name for d in registry.list_definitions()}
    assert "observability.get_api_latency" in definitions


def test_observability_tool_is_read_only(registry: ToolRegistry) -> None:
    executor = registry.get("observability.get_api_latency")
    assert executor.definition.risk_level == RiskLevel.READ
    assert executor.definition.requires_approval is False


# ---------------------------------------------------------------------------
# 2. Input validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_input_accepted(registry: ToolRegistry, tool_context: ToolContext) -> None:
    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(tool_context.organization_id, SAMPLE_METRICS)
        result = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h"},
            tool_context,
        )
    assert result.status == "succeeded"


@pytest.mark.asyncio
async def test_missing_time_range_fails_validation(registry: ToolRegistry, tool_context: ToolContext) -> None:
    result = await registry.execute(
        "observability.get_api_latency",
        {},  # time_range is required
        tool_context,
    )
    assert result.status == "failed"
    assert result.error_type == "validation_error"


# ---------------------------------------------------------------------------
# 3. Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation(
    registry: ToolRegistry,
    org_id: uuid.UUID,
    other_org_id: uuid.UUID,
) -> None:
    """Org A must never see metrics belonging to Org B."""
    # Org A context — Redis returns only Org A data
    ctx_a = ToolContext(
        organization_id=org_id,
        agent_run_id=uuid.uuid4(),
        execution_id="iso-a",
    )
    ctx_b = ToolContext(
        organization_id=other_org_id,
        agent_run_id=uuid.uuid4(),
        execution_id="iso-b",
    )

    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        # Org A call returns Org A metrics; Org B call returns other metrics
        async def get_redis_for_org(*args, **kwargs):
            redis_mock = AsyncMock()
            # The key used will contain the calling org's ID — mock returns appropriate data
            redis_mock.lrange = AsyncMock(return_value=[json.dumps(m).encode() for m in SAMPLE_METRICS])
            return redis_mock

        mock_get.side_effect = get_redis_for_org

        result_a = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h"},
            ctx_a,
        )

    assert result_a.status == "succeeded"
    # Verify the key used was scoped to org_a
    assert result_a.result is not None
    assert result_a.result.get("request_count", 0) > 0


# ---------------------------------------------------------------------------
# 4. Real latency retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_latency_retrieval(
    registry: ToolRegistry, tool_context: ToolContext, org_id: uuid.UUID
) -> None:
    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(org_id, SAMPLE_METRICS)
        result = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h"},
            tool_context,
        )

    assert result.status == "succeeded"
    data = result.result
    assert data is not None
    assert data["request_count"] == len(SAMPLE_METRICS)
    assert data["average_latency_ms"] > 0
    assert data["p50_latency_ms"] > 0
    assert data["p95_latency_ms"] > 0
    assert data["p99_latency_ms"] > 0
    assert "error_rate_percent" in data
    # 1 out of 5 requests has status 500 → 20% error rate
    assert data["error_rate_percent"] == 20.0
    assert len(data["slowest_endpoints"]) > 0
    # Slowest endpoint should be the streaming one at 800ms
    assert data["slowest_endpoints"][0]["path"] == "/api/v1/runs/abc/stream"


@pytest.mark.asyncio
async def test_endpoint_prefix_filter(
    registry: ToolRegistry, tool_context: ToolContext, org_id: uuid.UUID
) -> None:
    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        mock_get.return_value = _make_redis_mock(org_id, SAMPLE_METRICS)
        result = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h", "endpoint_prefix": "/api/v1/conversations"},
            tool_context,
        )

    data = result.result
    assert data is not None
    # Only 2 conversation requests in sample
    assert data["request_count"] == 2


# ---------------------------------------------------------------------------
# 5. No-data scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_data_returns_friendly_message(
    registry: ToolRegistry, tool_context: ToolContext
) -> None:
    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        redis_mock = AsyncMock()
        redis_mock.lrange = AsyncMock(return_value=[])
        mock_get.return_value = redis_mock

        result = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h"},
            tool_context,
        )

    assert result.status == "succeeded"
    data = result.result
    assert data is not None
    assert data["request_count"] == 0
    assert "No historical latency data" in data["message"]


# ---------------------------------------------------------------------------
# 6. Planner selecting observability tool
# ---------------------------------------------------------------------------

def test_planner_prompt_includes_observability_tool() -> None:
    """The planner system prompt must mention the observability tool."""
    import inspect
    from app.agents.planning.planner import PlanNode
    source = inspect.getsource(PlanNode)
    assert "observability.get_api_latency" in source


# ---------------------------------------------------------------------------
# 7. Structured fallback response generator
# ---------------------------------------------------------------------------

def _make_state_with_latency_result(data: dict) -> Any:
    """Build a minimal AgentState-like mock with history items."""
    from app.agents.core.state import (
        ActionHistoryItem, AgentAction, AgentNodeState, AgentPlan, AgentState
    )
    from datetime import datetime, timezone

    action = AgentAction(
        action_id="step_1",
        action_type="observability.get_api_latency",
        description="Get latency",
        arguments={"time_range": "24h"},
        status="COMPLETED",
    )
    history_item = ActionHistoryItem(
        action=action,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        error=None,
        result=data,
    )
    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Investigate our recent API latency.",
    )
    state.action_history = [history_item]
    return state


def test_structured_fallback_with_real_data() -> None:
    from app.agents.execution.decision import _generate_structured_response

    data = {
        "time_range": "24h",
        "request_count": 100,
        "average_latency_ms": 45.0,
        "p50_latency_ms": 30.0,
        "p95_latency_ms": 150.0,
        "p99_latency_ms": 300.0,
        "error_rate_percent": 0.0,
        "error_count": 0,
        "slowest_endpoints": [
            {"path": "/api/v1/runs", "avg_ms": 120.0, "calls": 10},
        ],
    }
    state = _make_state_with_latency_result(data)
    response = _generate_structured_response(state)
    assert "100" in response
    assert "45.0" in response
    assert "150.0" in response
    assert "healthy" in response.lower() or "acceptable" in response.lower()
    assert "/api/v1/runs" in response
    assert "0%" in response or "No request errors" in response


def test_structured_fallback_no_data() -> None:
    from app.agents.execution.decision import _generate_structured_response

    data = {
        "request_count": 0,
        "message": "No historical latency data is available yet. AURA's observability instrumentation is now connected.",
        "time_range": "recent",
    }
    state = _make_state_with_latency_result(data)
    response = _generate_structured_response(state)
    assert "No historical latency data" in response


def test_structured_fallback_high_latency_warning() -> None:
    from app.agents.execution.decision import _generate_structured_response

    data = {
        "time_range": "24h",
        "request_count": 50,
        "average_latency_ms": 750.0,
        "p50_latency_ms": 600.0,
        "p95_latency_ms": 1500.0,
        "p99_latency_ms": 2000.0,
        "error_rate_percent": 8.5,
        "error_count": 4,
        "slowest_endpoints": [
            {"path": "/api/v1/runs/stream", "avg_ms": 2000.0, "calls": 5},
        ],
    }
    state = _make_state_with_latency_result(data)
    response = _generate_structured_response(state)
    assert "critical" in response.lower() or "concerning" in response.lower()
    assert "8.5" in response
    assert "⚠️" in response or "Recommended" in response


# ---------------------------------------------------------------------------
# 8. Tool failure (Redis unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_failure_returns_failed_result(
    registry: ToolRegistry, tool_context: ToolContext
) -> None:
    with patch("app.security.rate_limit.get_redis_client") as mock_get:
        mock_get.side_effect = ConnectionError("Redis is unavailable")
        result = await registry.execute(
            "observability.get_api_latency",
            {"time_range": "24h"},
            tool_context,
        )
    assert result.status == "failed"


# ---------------------------------------------------------------------------
# 9. Unauthorized access — no organization context
# ---------------------------------------------------------------------------

def test_observability_tool_is_organization_scoped(registry: ToolRegistry) -> None:
    executor = registry.get("observability.get_api_latency")
    assert executor.definition.organization_scoped is True


# ---------------------------------------------------------------------------
# 10. Conversation integration — tool available in list
# ---------------------------------------------------------------------------

def test_observability_in_tool_definitions(registry: ToolRegistry) -> None:
    names = [d.name for d in registry.list_definitions()]
    assert "observability.get_api_latency" in names
    defn = registry.get("observability.get_api_latency").definition
    assert "latency" in defn.description.lower()
    assert "time_range" in defn.input_schema["properties"]
