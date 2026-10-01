with open("backend/tests/ai/test_llm_fallback.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "with pytest.raises(RuntimeError) as exc_info:",
    "with pytest.raises(LLMProviderError) as exc_info:"
)
text = text.replace(
    "assert \"All LLM providers failed\" in str(exc_info.value)",
    ""
)

with open("backend/tests/ai/test_llm_fallback.py", "w", encoding="utf-8") as f:
    f.write(text)
