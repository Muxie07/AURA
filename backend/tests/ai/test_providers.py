import pytest
from pydantic import BaseModel

from app.ai.providers.mock import MockLLMProvider
from app.ai.schemas.generation import GenerationRequest, Message


class IntentResult(BaseModel):
    intent: str
    confidence: float


@pytest.mark.asyncio
async def test_mock_provider_generate() -> None:
    provider = MockLLMProvider()
    request = GenerationRequest(
        messages=[Message(role="user", content="What is 2 + 2?")], model="mock-model"
    )
    result = await provider.generate(request)
    assert result.text == "4"
    assert result.provider == "mock"


@pytest.mark.asyncio
async def test_mock_provider_generate_structured() -> None:
    provider = MockLLMProvider()
    request = GenerationRequest(
        messages=[Message(role="user", content="hello")], model="mock-model"
    )
    _, parsed = await provider.generate_structured(request, IntentResult)
    assert parsed.intent == "general_inquiry"
