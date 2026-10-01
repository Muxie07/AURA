import uuid

import pytest

from app.agents.core.builtin_nodes import ExecutionNode
from app.agents.core.graph import WorkflowGraph
from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentNodeState, AgentState, FailureCategory
from app.tools.registry import ToolRegistry


class DummyInfiniteNode(BaseNode):
    @property
    def name(self):
        return "DummyInfiniteNode"

    async def _execute(self, state, **kwargs):
        state.status = AgentNodeState.PLANNING
        return state


class HallucinatedToolNode(BaseNode):
    @property
    def name(self):
        return "HallucinatedToolNode"

    async def _execute(self, state, **kwargs):
        from app.agents.core.state import AgentAction

        state.current_actions.append(
            AgentAction(action_type="non_existent_tool", description="Test")
        )
        state.status = AgentNodeState.EXECUTING
        return state


@pytest.mark.asyncio
async def test_infinite_loop_prevention():
    graph = WorkflowGraph()
    graph.add_node(AgentNodeState.CREATED, DummyInfiniteNode())
    graph.add_node(AgentNodeState.PLANNING, DummyInfiniteNode())
    graph.add_transition(AgentNodeState.CREATED, lambda s: AgentNodeState.PLANNING)
    graph.add_transition(AgentNodeState.PLANNING, lambda s: AgentNodeState.CREATED)

    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="test",
    )

    # Run the graph; it should hit max_agent_iterations limit
    final_state = await graph.run(state)
    assert final_state.status == AgentNodeState.TIMEOUT


@pytest.mark.asyncio
async def test_hallucinated_tool_call():
    registry = ToolRegistry()
    node = ExecutionNode(registry)
    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="test",
    )
    from app.agents.core.state import AgentAction

    state.current_actions.append(AgentAction(action_type="hallucinated_tool", description="Hack"))

    final_state = await node._execute(state)
    assert len(final_state.errors) > 0
    assert final_state.errors[0].category == FailureCategory.VALIDATION
    assert "Unknown tool type" in final_state.errors[0].message


@pytest.mark.asyncio
async def test_agent_cancellation():
    class CancellableNode(BaseNode):
        @property
        def name(self):
            return "CancellableNode"

        async def _execute(self, state, **kwargs):
            if state.status == AgentNodeState.CANCELLED:
                return state
            state.status = AgentNodeState.COMPLETED
            return state

    graph = WorkflowGraph()
    graph.add_node(AgentNodeState.CREATED, CancellableNode())
    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="test",
        status=AgentNodeState.CANCELLED,
    )
    final_state = await graph.run(state)
    assert final_state.status == AgentNodeState.CANCELLED
