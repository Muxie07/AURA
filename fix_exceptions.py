with open("backend/app/ai/errors/exceptions.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "class LLMRateLimitError(LLMProviderError):",
    "class LLMRateLimitError(LLMProviderError):\n    \"\"\"Raised when an LLM provider rate limit is exceeded.\"\"\"\n    pass\n\nclass LLMQuotaExceededError(LLMProviderError):\n    \"\"\"Raised when a hard daily quota is exhausted (do not retry).\"\"\"\n    def __init__(self, message: str, provider: str = 'unknown', status: int = 429):\n        super().__init__(message)\n        self.provider = provider\n        self.status = status"
)

with open("backend/app/ai/errors/exceptions.py", "w", encoding="utf-8") as f:
    f.write(text)
