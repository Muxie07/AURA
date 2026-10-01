with open("backend/tests/ai/test_llm_fallback.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from app.core.exceptions import LLMRateLimitError, LLMProviderError",
    "from app.ai.errors.exceptions import LLMRateLimitError, LLMProviderError"
)

with open("backend/tests/ai/test_llm_fallback.py", "w", encoding="utf-8") as f:
    f.write(text)
