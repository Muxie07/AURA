class AURAError(Exception):
    pass


class LLMProviderError(AURAError):
    pass


class LLMTimeoutError(LLMProviderError):
    pass


class LLMRateLimitError(LLMProviderError):
    pass


class LLMQuotaExceededError(LLMProviderError):
    def __init__(self, message: str, provider: str = "unknown", status: int = 429):
        super().__init__(message)
        self.provider = provider
        self.status = status


class LLMAuthenticationError(LLMProviderError):
    pass


class LLMValidationError(LLMProviderError):
    pass


class PromptNotFoundError(AURAError):
    pass


class ModelRoutingError(AURAError):
    pass


class LLMContentBlockedError(LLMProviderError):
    pass
