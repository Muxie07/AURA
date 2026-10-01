import uuid

import pytest

from app.agents.core.graph import WorkflowGraph
from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentNodeState, AgentState


class DummyNode(BaseNode):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def _execute(self, state: AgentState, **kwargs) -> AgentState:
        return state

class ErrorNode(BaseNode):
    @property
    def name(self) -> str:
        return "ErrorNode"

    async def _execute(self, state: AgentState, **kwargs) -> AgentState:
        raise ValueError("Boom")

@pytest.mark.asyncio
async def test_agent_state_machine_valid_flow():
    graph = WorkflowGraph()
    graph.add_node(AgentNodeState.CREATED, DummyNode("N1"))
    graph.add_node(AgentNodeState.PLANNING, DummyNode("N2"))
    graph.add_transition(AgentNodeState.CREATED, lambda s: AgentNodeState.PLANNING)
    graph.add_transition(AgentNodeState.PLANNING, lambda s: AgentNodeState.COMPLETED)

    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Test request"
    )

    final_state = await graph.run(state)
    assert final_state.status == AgentNodeState.COMPLETED
    assert final_state.iteration_count == 2

@pytest.mark.asyncio
async def test_agent_state_machine_failure():
    graph = WorkflowGraph()
    graph.add_node(AgentNodeState.CREATED, ErrorNode())

    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Test request"
    )

    final_state = await graph.run(state)
    assert final_state.status == AgentNodeState.FAILED
    assert len(final_state.errors) == 1
    assert "Boom" in final_state.errors[0].message

@pytest.mark.asyncio
async def test_agent_max_iterations():
    from app.agents.core.limits import limits
    original = limits.max_agent_iterations
    limits.max_agent_iterations = 3

    graph = WorkflowGraph()
    # Create an infinite loop
    graph.add_node(AgentNodeState.CREATED, DummyNode("N1"))
    graph.add_node(AgentNodeState.PLANNING, DummyNode("N2"))
    graph.add_transition(AgentNodeState.CREATED, lambda s: AgentNodeState.PLANNING)
    graph.add_transition(AgentNodeState.PLANNING, lambda s: AgentNodeState.CREATED)

    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Test request"
    )

    final_state = await graph.run(state)
    assert final_state.status == AgentNodeState.TIMEOUT
    assert final_state.iteration_count > 3

    limits.max_agent_iterations = original
