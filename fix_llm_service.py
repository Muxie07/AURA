with open("backend/app/ai/services/llm.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# We need to make sure we don't wrap LLMQuotaExceededError in RuntimeError if we don't have a fallback or fallback fails.
# Actually, it's better to just raise the original error e if it's LLMQuotaExceededError or LLMProviderError, instead of RuntimeError.
replacement = """            # If all fail, raise the original exception so the domain error reaches the caller
            raise e"""

text = re.sub(r'            # If all fail, raise clear error\n\s*raise RuntimeError\(f"All LLM providers failed\. Primary error: \{str\(e\)\}"\) from e', replacement, text, flags=re.DOTALL)
text = re.sub(r'            raise RuntimeError\(f"All LLM structured providers failed\. Primary error: \{str\(e\)\}"\) from e', '            raise e', text, flags=re.DOTALL)

with open("backend/app/ai/services/llm.py", "w", encoding="utf-8") as f:
    f.write(text)
