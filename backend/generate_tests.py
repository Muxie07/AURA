import os

os.makedirs('tests/ai', exist_ok=True)

test_providers_content = '''
import pytest
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.providers.mock import MockLLMProvider
from pydantic import BaseModel

class DummyResult(BaseModel):
    intent: str
    confidence: float

@pytest.mark.asyncio
async def test_mock_provider_generate():
    provider = MockLLMProvider()
    request = GenerationRequest(
        messages=[Message(role="user", content="What is 2 + 2?")],
        model="mock-model"
    )
    result = await provider.generate(request)
    assert result.text == "4"
    assert result.provider == "mock"

@pytest.mark.asyncio
async def test_mock_provider_generate_structured():
    provider = MockLLMProvider()
    request = GenerationRequest(
        messages=[Message(role="user", content="hello")],
        model="mock-model"
    )
    result, parsed = await provider.generate_structured(request, DummyResult)
    assert parsed.intent == "create_quotation"
'''
with open('tests/ai/test_providers.py', 'w') as f: f.write(test_providers_content)

test_factory_content = '''
import pytest
from app.ai.providers.factory import get_llm_provider
from app.ai.providers.mock import MockLLMProvider
from app.ai.providers.openai import OpenAIProvider
from app.config.settings import get_settings

def test_get_mock_provider(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)

def test_get_openai_provider(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)
'''
with open('tests/ai/test_factory.py', 'w') as f: f.write(test_factory_content)

test_service_content = '''
import pytest
from app.ai.services.llm import LLMService
from app.config.settings import get_settings

@pytest.mark.asyncio
async def test_llm_service_simple(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    get_settings.cache_clear()

    service = LLMService()
    text = await service.generate_simple("What is 2 + 2?")
    assert text == "4"
'''
with open('tests/ai/test_service.py', 'w') as f: f.write(test_service_content)

test_router_content = '''
from app.ai.routing.router import ModelRouter
from app.config.settings import get_settings

def test_model_router(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "test-model-42")
    get_settings.cache_clear()
    assert ModelRouter.get_model_for_task("general") == "test-model-42"
'''
with open('tests/ai/test_router.py', 'w') as f: f.write(test_router_content)

test_registry_content = '''
import pytest
from app.ai.prompts.registry import PromptRegistry
from app.ai.errors.exceptions import PromptNotFoundError

def test_registry_get_valid():
    prompt = PromptRegistry.get("default:v1")
    assert "AURA" in prompt

def test_registry_get_invalid():
    with pytest.raises(PromptNotFoundError):
        PromptRegistry.get("invalid_does_not_exist:v1")
'''
with open('tests/ai/test_registry.py', 'w') as f: f.write(test_registry_content)

test_ai_endpoints_content = '''
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_generate(async_client: AsyncClient, access_token: str, monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    from app.config.settings import get_settings
    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post(
        "/api/v1/ai/generate",
        json={"message": "Explain what AURA does."},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "AURA is an autonomous" in data["text"]

@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_classify(async_client: AsyncClient, access_token: str, monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    from app.config.settings import get_settings
    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post(
        "/api/v1/ai/classify",
        json={"text": "I need a quotation"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "create_quotation"
'''
with open('tests/test_ai_endpoints.py', 'w') as f: f.write(test_ai_endpoints_content)
