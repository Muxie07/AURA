with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "def generate(self, request: GenerationRequest) -> GenerationResult:\n        raise LLMQuotaExceededError('Simulated 429 quota exhaustion', provider='gemini', status=429)",
    "async def generate(self, request: GenerationRequest) -> GenerationResult:\n        raise LLMQuotaExceededError('Simulated 429 quota exhaustion', provider='gemini', status=429)"
)

text = text.replace(
    "def generate_structured(\n        self, request: GenerationRequest, schema: type[T]\n    ) -> tuple[GenerationResult, T]:\n        raise LLMQuotaExceededError('Simulated 429 quota exhaustion', provider='gemini', status=429)",
    "async def generate_structured(\n        self, request: GenerationRequest, schema: type[T]\n    ) -> tuple[GenerationResult, T]:\n        raise LLMQuotaExceededError('Simulated 429 quota exhaustion', provider='gemini', status=429)"
)

with open("backend/app/ai/providers/google.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed syntax in google.py")
