from app.ai.providers.base import LLMProvider
from app.config.settings import get_settings


def get_llm_provider(provider_override: str | None = None) -> LLMProvider:
    settings = get_settings()
    provider_name = provider_override or settings.primary_llm_provider.lower()

    if provider_name == "openai":
        from app.ai.providers.openai import OpenAIProvider

        return OpenAIProvider()
    elif provider_name in ["google", "gemini"]:
        from app.ai.providers.google import GeminiProvider

        return GeminiProvider()
    elif provider_name == "heuristic":
        from app.ai.providers.heuristic import HeuristicLLMProvider

        return HeuristicLLMProvider()
    else:
        from app.ai.providers.mock import MockLLMProvider

        return MockLLMProvider()
