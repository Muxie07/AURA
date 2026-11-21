with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "async def generate(self, request: GenerationRequest) -> GenerationResult:\n        return await self._old_generate",
    "async def generate(self, request: GenerationRequest) -> GenerationResult:\n        from app.ai.errors.exceptions import LLMQuotaExceededError\n        raise LLMQuotaExceededError('Simulated 429 quota exhaustion', provider='gemini', status=429)"
)

# wait, _old_generate is used... let's just raise it inside generate directly. 
# actually earlier I just replaced the `async def generate...` body.
