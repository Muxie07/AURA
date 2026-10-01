with open("backend/tests/ai/test_llm_fallback.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message, TokenUsage",
    "from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message\nfrom app.ai.schemas.usage import Usage as TokenUsage"
)

with open("backend/tests/ai/test_llm_fallback.py", "w", encoding="utf-8") as f:
    f.write(text)
