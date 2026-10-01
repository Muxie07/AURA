from typing import Any

from app.ai.providers.factory import get_llm_provider
from app.ai.providers.mock import MockLLMProvider
from app.ai.providers.openai import OpenAIProvider
from app.config.settings import get_settings


def test_get_mock_provider(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)

def test_get_openai_provider(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)

def test_get_google_provider(monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "dummy")
    get_settings.cache_clear()
    from app.ai.providers.google import GeminiProvider
    provider = get_llm_provider()
    assert isinstance(provider, GeminiProvider)
