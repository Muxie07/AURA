from unittest.mock import AsyncMock, patch

import pytest

from app.ai.errors.exceptions import LLMProviderError
from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message
from app.ai.schemas.usage import Usage as TokenUsage
from app.ai.services.llm import LLMService
from app.config.settings import ModelProvider, get_settings


@pytest.fixture
def mock_settings():
    settings = get_settings()
    # Reset fallbacks
    settings.fallback_llm_provider = None
    settings.fallback_llm_model = None
    return settings


@pytest.fixture
def base_request():
    return GenerationRequest(
        messages=[Message(role="user", content="Hello")], model="primary-model"
    )


@pytest.mark.asyncio
async def test_llm_service_no_fallback_no_attribute_error(mock_settings, base_request):
    """A. LLMService with no fallback does not raise AttributeError."""
    # Ensure no fallback is set
    mock_settings.fallback_llm_provider = None

    with patch("app.ai.services.llm.get_llm_provider") as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary

        service = LLMService()
        assert service.fallback_provider is None

        # Test success case
        mock_primary.generate.return_value = GenerationResult(
            text="Success",
            model="primary-model",
            provider="mock",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

        result = await service.generate_with_fallback(base_request)
        assert result.text == "Success"


@pytest.mark.asyncio
async def test_primary_provider_success(mock_settings, base_request):
    """B. Primary provider success works."""
    with patch("app.ai.services.llm.get_llm_provider") as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary

        service = LLMService()

        mock_primary.generate.return_value = GenerationResult(
            text="Primary Success",
            model="primary-model",
            provider="primary",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

        result = await service.generate_with_fallback(base_request)
        assert result.text == "Primary Success"
        mock_primary.generate.assert_called_once()


@pytest.mark.asyncio
async def test_primary_provider_429_with_fallback(mock_settings, base_request):
    """C. Primary provider 429 + configured fallback uses fallback."""
    mock_settings.fallback_llm_provider = ModelProvider.OPENAI
    mock_settings.fallback_llm_model = "fallback-model"

    with patch("app.ai.services.llm.get_llm_provider") as mock_factory:
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()

        def factory_side_effect(provider_name=None):
            if provider_name == ModelProvider.OPENAI:
                return mock_fallback
            return mock_primary

        mock_factory.side_effect = factory_side_effect

        service = LLMService()

        # Primary fails with provider error (e.g. quota exhausted 429)
        mock_primary.generate.side_effect = LLMProviderError("Gemini quota exhausted")

        # Fallback succeeds
        mock_fallback.generate.return_value = GenerationResult(
            text="Fallback Success",
            model="fallback-model",
            provider="openai",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

        result = await service.generate_with_fallback(base_request)
        assert result.text == "Fallback Success"
        assert result.model == "fallback-model"
        mock_primary.generate.assert_called_once()
        mock_fallback.generate.assert_called_once()


@pytest.mark.asyncio
async def test_primary_provider_429_no_fallback(mock_settings, base_request):
    """D. Primary provider 429 + no fallback returns a clean controlled error."""
    mock_settings.fallback_llm_provider = None

    with patch("app.ai.services.llm.get_llm_provider") as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary

        service = LLMService()

        # Primary fails
        mock_primary.generate.side_effect = LLMProviderError("Gemini quota exhausted")

        with pytest.raises(LLMProviderError) as exc_info:
            await service.generate_with_fallback(base_request)

        assert "Gemini quota exhausted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_heuristic_p1_incident_does_not_mention_latency():
    """Verify that asking for a P1 incident procedure never mentions API latency."""
    from app.ai.providers.heuristic import HeuristicLLMProvider

    provider = HeuristicLLMProvider()
    req = GenerationRequest(
        messages=[Message(role="user", content="Find the procedure for handling a P1 incident")],
        model="heuristic-fallback",
    )
    result = await provider.generate(req)
    assert "latency" not in result.text.lower()
    assert "p1" in result.text.lower() or "incident" in result.text.lower() or "procedure" in result.text.lower()


@pytest.mark.asyncio
async def test_heuristic_synthesizes_rag_context():
    """Verify that heuristic provider surfaces RAG documentation when present."""
    from app.ai.providers.heuristic import HeuristicLLMProvider

    provider = HeuristicLLMProvider()
    content = (
        "Original Request: Find the procedure for handling a P1 incident\n"
        "--- RAG CONTEXT ---\n"
        "Source: runbooks/p1.md\n"
        "Step 1: Declare incident. Step 2: Notify on-call. Step 3: Open bridge."
    )
    req = GenerationRequest(
        messages=[Message(role="user", content=content)],
        model="heuristic-fallback",
    )
    result = await provider.generate(req)
    assert "Declare incident" in result.text
    assert "latency" not in result.text.lower()


@pytest.mark.asyncio
async def test_decision_node_structured_response_formatting():
    """Verify _generate_structured_response generates detailed latency report from tool results."""
    import uuid
    from datetime import datetime, timezone

    from app.agents.core.state import ActionHistoryItem, AgentAction, AgentNodeState, AgentState
    from app.agents.execution.decision import _generate_structured_response

    state = AgentState(
        run_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Investigate API latency",
        status=AgentNodeState.UNDERSTANDING,
    )
    action = AgentAction(
        action_id="step_1",
        action_type="observability.get_api_latency",
        description="Check latency",
        arguments={"time_range": "24h"},
        status="SUCCESS",
    )
    history_item = ActionHistoryItem(
        action=action,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        result={
            "request_count": 500,
            "average_latency_ms": 45,
            "p50_latency_ms": 30,
            "p95_latency_ms": 85,
            "p99_latency_ms": 120,
            "error_rate_percent": 0.0,
            "error_count": 0,
            "slowest_endpoints": [],
            "time_range": "24h",
        },
    )
    state.action_history.append(history_item)

    response = _generate_structured_response(state)
    assert "API Performance Report" in response
    assert "500 requests" in response
    assert "P50 (median): 30 ms" in response
    assert "P95: 85 ms" in response
    assert "P99: 120 ms" in response
    assert "HEALTHY" in response



@pytest.mark.asyncio
async def test_decision_node_skips_llm_stream_when_tool_results_exist():
    """Regression: DecisionNode must NOT call LLM.stream() after tools have executed.

    Previously, when all plan steps were done and action_history was non-empty,
    DecisionNode streamed through the LLM first. When the primary (Google) was
    quota-limited, the heuristic fallback streamed "I'm currently operating in
    offline fallback mode. I can help you investigate API latency." to Redis
    before the structured override could fire — so the browser saw the wrong text.

    After the fix: action_history is checked FIRST; _generate_structured_response
    is called directly; self.llm.stream() is never called.
    """
    import uuid
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from app.agents.core.state import (
        ActionHistoryItem,
        AgentAction,
        AgentNodeState,
        AgentState,
    )
    from app.agents.execution.decision import DecisionNode
    from app.agents.planning.schemas import PlannedStep, StructuredAgentPlan

    run_id = uuid.uuid4()
    state = AgentState(
        run_id=run_id,
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="Investigate our recent API latency.",
        status=AgentNodeState.UNDERSTANDING,
    )
    step = PlannedStep(
        id="step_1",
        type="observability.get_api_latency",
        description="Get API latency",
        dependencies=[],
        required_tools=["observability.get_api_latency"],
        risk="LOW",
        expected_output="Metrics",
        verification_criteria="Non-empty metrics",
    )
    state.plan = StructuredAgentPlan(goal="Investigate API latency", steps=[step])

    action = AgentAction(
        action_id="step_1",
        action_type="observability.get_api_latency",
        description="Get API latency",
        arguments={"time_range": "24h"},
        status="SUCCESS",
    )
    history_item = ActionHistoryItem(
        action=action,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        result={
            "request_count": 250,
            "average_latency_ms": 55,
            "p50_latency_ms": 40,
            "p95_latency_ms": 100,
            "p99_latency_ms": 180,
            "error_rate_percent": 0.0,
            "error_count": 0,
            "slowest_endpoints": [],
            "time_range": "24h",
        },
    )
    state.action_history.append(history_item)

    stream_was_called = False

    class FakeLLM:
        async def stream(self, req):
            nonlocal stream_was_called
            stream_was_called = True
            yield "SHOULD NOT BE REACHED"

    published_chunks: list[str] = []

    class FakeRedis:
        async def publish(self, channel: str, data: str) -> None:
            published_chunks.append(data)

        async def aclose(self) -> None:
            pass

    node = DecisionNode(FakeLLM())

    with patch("redis.asyncio.from_url", return_value=FakeRedis()):
        result_state = await node._execute(state)

    assert not stream_was_called, "LLM.stream() must NOT be called when action_history is non-empty"
    assert result_state.status == AgentNodeState.COMPLETED
    final = result_state.final_response or ""
    assert "offline fallback mode" not in final, (
        f"Offline fallback text must not appear. Got: {final[:200]}"
    )
    assert "API Performance Report" in final or "250" in final, (
        f"Structured response must contain tool data. Got: {final[:200]}"
    )
    combined = " ".join(published_chunks)
    assert "offline fallback mode" not in combined, (
        "Offline fallback text must not be published to Redis"
    )
    assert published_chunks, "At least one chunk must have been published to Redis"


@pytest.mark.asyncio
async def test_decision_node_uses_llm_when_no_tool_results():
    """When action_history is empty and no plan steps, DecisionNode uses the LLM stream normally."""
    import uuid
    from unittest.mock import MagicMock

    from app.agents.core.state import AgentNodeState, AgentState
    from app.agents.execution.decision import DecisionNode
    from app.agents.planning.schemas import StructuredAgentPlan

    run_id = uuid.uuid4()
    state = AgentState(
        run_id=run_id,
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        original_request="What time is it?",
        status=AgentNodeState.UNDERSTANDING,
    )
    state.plan = StructuredAgentPlan(goal="Answer general question", steps=[])

    llm_chunks = ["The time is ", "unknown without ", "a clock tool."]

    class FakeLLM:
        async def stream(self, req):
            for chunk in llm_chunks:
                yield chunk

    published_chunks: list[str] = []

    class FakeRedis:
        async def publish(self, channel: str, data: str) -> None:
            published_chunks.append(data)

        async def aclose(self) -> None:
            pass

    node = DecisionNode(FakeLLM())

    with patch("redis.asyncio.from_url", return_value=FakeRedis()):
        result_state = await node._execute(state)

    assert result_state.status == AgentNodeState.COMPLETED
    assert "".join(llm_chunks) == result_state.final_response
    assert published_chunks == llm_chunks
