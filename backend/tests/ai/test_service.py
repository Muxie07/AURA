import uuid
from typing import Any

import pytest

from app.ai.errors.exceptions import LLMTimeoutError
from app.ai.providers.base import LLMProvider
from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message
from app.ai.services.llm import LLMService
from app.config.settings import get_settings
from app.evaluation.cost import CostManager


@pytest.mark.asyncio
async def test_llm_service_simple(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    service = LLMService()
    text = await service.generate_simple("What is 2 + 2?")
    assert text == "4"


@pytest.mark.asyncio
async def test_llm_service_budget_enforcement(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    org_id = uuid.uuid4()
    await CostManager.reset_daily_spend(org_id)

    service = LLMService()

    # Very long prompt to trigger budget exceeded
    messages = [Message(role="user", content="A" * 30000000)]
    request = GenerationRequest(messages=messages, model="gpt-4-turbo", organization_id=org_id)

    with pytest.raises(Exception, match="Budget exceeded"):
        await service.generate(request)


@pytest.mark.asyncio
async def test_llm_service_fallback(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    get_settings.cache_clear()

    org_id = uuid.uuid4()
    await CostManager.reset_daily_spend(org_id)

    service = LLMService()

    # Mock the provider to raise a timeout on the first call, but succeed on fallback
    class MockProviderWithTimeout(LLMProvider):
        name = "mock"

        async def generate(self, request: GenerationRequest) -> GenerationResult:
            if request.model == "failing-model":
                raise LLMTimeoutError("Timeout")
            from app.ai.schemas.usage import Usage

            return GenerationResult(
                text="fallback success",
                model=request.model,
                provider="mock",
                usage=Usage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            )

        async def generate_structured(self, request: Any, schema: Any) -> Any:
            raise NotImplementedError()

        async def stream(self, request: Any) -> Any:  # type: ignore
            raise NotImplementedError()

        async def embed(self, texts: list[str], model: str) -> list[list[float]]:
            raise NotImplementedError()

    service.provider = MockProviderWithTimeout()

    request = GenerationRequest(
        messages=[Message(role="user", content="Hello")],
        model="failing-model",
        organization_id=org_id,
    )

    # Monkeypatch get_retry_decorator to not retry, just raise immediately to test fallback
    def no_retry() -> Any:
        def decorator(func: Any) -> Any:
            return func

        return decorator

    monkeypatch.setattr(service, "_get_retry_decorator", no_retry)

    result = await service.generate_with_fallback(request, fallback_model="gpt-4o-mini")

    assert result.text == "fallback success"
    assert result.model == "gpt-4o-mini"
    assert result.usage.estimated_cost is not None
