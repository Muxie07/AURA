class AURAError(Exception):
    """Base exception for all AURA domain errors."""
    pass

class LLMProviderError(AURAError):
    """Base class for all LLM provider errors."""
    pass

class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider request times out."""
    pass

class LLMRateLimitError(LLMProviderError):
    """Raised when an LLM provider rate limit is exceeded."""
    pass

class LLMQuotaExceededError(LLMProviderError):
    """Raised when a hard daily quota is exhausted (do not retry)."""
    def __init__(self, message: str, provider: str = 'unknown', status: int = 429):
        super().__init__(message)
        self.provider = provider
        self.status = status

class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with an LLM provider fails."""
    pass

class LLMValidationError(LLMProviderError):
    """Raised when structured output fails validation against a requested schema."""
    pass

class PromptNotFoundError(AURAError):
    """Raised when a requested prompt is not found in the registry."""
    pass

class ModelRoutingError(AURAError):
    """Raised when no suitable model can be routed for a task."""
    pass
