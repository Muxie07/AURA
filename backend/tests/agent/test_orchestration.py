import uuid

import pytest

from app.agents.core.builtin_nodes import ExecutionNode
from app.agents.core.state import AgentNodeState, AgentPlan, AgentPlanStep, AgentState
from app.agents.execution.decision import DecisionNode
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyDecision
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_parallel_dependencies(monkeypatch):
    state = AgentState(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Test parallel orchestration",
        run_id=uuid.uuid4(),
        status=AgentNodeState.UNDERSTANDING,
        plan=AgentPlan(
            goal="Test",
            steps=[
                AgentPlanStep(id="A", type="test_tool", description="A"),
                AgentPlanStep(id="B", type="test_tool", description="B"),
                AgentPlanStep(id="C", type="test_tool", description="C", dependencies=["A", "B"]),
            ],
        ),
    )

    class MockLLM:
        async def generate_structured(self, *args, **kwargs):
            class MockDecision:
                class MockAction:
                    def __init__(self, id):
                        self.action_id = id
                        self.action_type = "test_tool"
                        self.arguments = {}
                        self.reasoning = "test"

                actions = [MockAction("A"), MockAction("B")]

            return None, MockDecision()

    decision_node = DecisionNode(MockLLM())
    state = await decision_node._execute(state)

    assert state.status == AgentNodeState.READY_TO_EXECUTE
    assert len(state.current_actions) == 2
    assert {a.action_id for a in state.current_actions} == {"A", "B"}

    class MockTool:
        class MockDef:
            name = "test_tool"
            risk_level = "LOW"
            source = "builtin"
            version = "1.0"

        definition = MockDef()

        async def execute(self, *args, **kwargs):
            class MockResult:
                status = "success"
                result = "ok"

            return MockResult()

    registry = ToolRegistry()
    registry.register(MockTool())

    class MockPolicyDecision:
        decision = PolicyDecision.ALLOW

    monkeypatch.setattr(PolicyEngine, "evaluate", lambda ctx: MockPolicyDecision())

    exec = ExecutionNode(registry)
    state = await exec._execute(state)
    assert len(state.action_history) == 2

    class MockLLM2:
        async def generate_structured(self, *args, **kwargs):
            class MockDecision2:
                class MockAction2:
                    def __init__(self, id):
                        self.action_id = id
                        self.action_type = "test_tool"
                        self.arguments = {}
                        self.reasoning = "test"

                actions = [MockAction2("C")]

            return None, MockDecision2()

    decision_node2 = DecisionNode(MockLLM2())
    state = await decision_node2._execute(state)
    assert len(state.current_actions) == 1
    assert state.current_actions[0].action_id == "C"
