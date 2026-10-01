import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.agents.core.builtin_nodes import ReplanNode
from app.agents.core.state import AgentLimits, AgentNodeState, AgentState, FailureCategory


def get_dummy_state(**kwargs):
    default_kwargs = {
        "run_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
        "original_request": "test",
    }
    default_kwargs.update(kwargs)
    return AgentState(**default_kwargs)


@pytest.mark.asyncio
async def test_replan_node_timeout():
    state = get_dummy_state(
        started_at=datetime.now(UTC) - timedelta(seconds=400),
        limits=AgentLimits(overall_timeout_seconds=300),
    )
    node = ReplanNode(None)
    res = await node._execute(state)
    assert res.status == AgentNodeState.FAILED
    assert "timed out" in str(res.errors[0].message)


@pytest.mark.asyncio
async def test_replan_node_max_tool_calls():
    state = get_dummy_state(limits=AgentLimits(max_tool_calls=2))
    state.action_history.extend(["dummy", "dummy"])
    node = ReplanNode(None)
    res = await node._execute(state)
    assert res.status == AgentNodeState.FAILED
    assert "Max tool calls" in str(res.errors[0].message)


@pytest.mark.asyncio
async def test_replan_node_max_retries():
    state = get_dummy_state(limits=AgentLimits(max_retries=2))
    state.retry_count = 3
    state.add_error(FailureCategory.TOOL_FAILURE, "test")
    node = ReplanNode(None)
    res = await node._execute(state)
    assert res.status == AgentNodeState.FAILED
    assert "Max retries" in str(res.errors[-1].message)


@pytest.mark.asyncio
async def test_replan_node_max_replans():
    state = get_dummy_state(limits=AgentLimits(max_replan_attempts=2))
    state.replans = 3
    node = ReplanNode(None)
    res = await node._execute(state)
    assert res.status == AgentNodeState.FAILED
    assert "Max replan" in str(res.errors[-1].message)


@pytest.mark.asyncio
async def test_replan_node_success():
    state = get_dummy_state(limits=AgentLimits(max_replan_attempts=2))
    node = ReplanNode(None)
    res = await node._execute(state)
    assert res.status == AgentNodeState.PLANNING
