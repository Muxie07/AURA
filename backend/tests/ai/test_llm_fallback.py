import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.services.llm import LLMService
from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message
from app.ai.schemas.usage import Usage as TokenUsage
from app.config.settings import get_settings, ModelProvider
from app.ai.errors.exceptions import LLMRateLimitError, LLMProviderError

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
        messages=[Message(role="user", content="Hello")],
        model="primary-model"
    )

@pytest.mark.asyncio
async def test_llm_service_no_fallback_no_attribute_error(mock_settings, base_request):
    """A. LLMService with no fallback does not raise AttributeError."""
    # Ensure no fallback is set
    mock_settings.fallback_llm_provider = None
    
    with patch('app.ai.providers.factory.get_llm_provider') as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary
        
        service = LLMService()
        assert service.fallback_provider is None
        
        # Test success case
        mock_primary.generate.return_value = GenerationResult(
            text="Success",
            model="primary-model",
            provider="mock",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
        )
        
        result = await service.generate_with_fallback(base_request)
        assert result.text == "Success"

@pytest.mark.asyncio
async def test_primary_provider_success(mock_settings, base_request):
    """B. Primary provider success works."""
    with patch('app.ai.providers.factory.get_llm_provider') as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary
        
        service = LLMService()
        
        mock_primary.generate.return_value = GenerationResult(
            text="Primary Success",
            model="primary-model",
            provider="primary",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
        )
        
        result = await service.generate_with_fallback(base_request)
        assert result.text == "Primary Success"
        mock_primary.generate.assert_called_once()

@pytest.mark.asyncio
async def test_primary_provider_429_with_fallback(mock_settings, base_request):
    """C. Primary provider 429 + configured fallback uses fallback."""
    mock_settings.fallback_llm_provider = ModelProvider.OPENAI
    mock_settings.fallback_llm_model = "fallback-model"
    
    with patch('app.ai.providers.factory.get_llm_provider') as mock_factory:
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
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
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
    
    with patch('app.ai.providers.factory.get_llm_provider') as mock_factory:
        mock_primary = AsyncMock()
        mock_factory.return_value = mock_primary
        
        service = LLMService()
        
        # Primary fails
        mock_primary.generate.side_effect = LLMProviderError("Gemini quota exhausted")
        
        with pytest.raises(LLMProviderError) as exc_info:
            await service.generate_with_fallback(base_request)
            
        
        assert "Gemini quota exhausted" in str(exc_info.value)
