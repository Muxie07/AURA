with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r'from app\.ai\.errors\.exceptions import.*?\n', 'from app.ai.errors.exceptions import LLMProviderError, LLMTimeoutError, LLMRateLimitError, LLMAuthenticationError, LLMQuotaExceededError\n', text, count=1)

replacement = """                    if "GenerateRequestsPerDay" in str(e) or "quota" in str(e).lower():
                        return LLMQuotaExceededError(f"Gemini quota exhausted (429): {e}", provider="gemini", status=429)"""

text = re.sub(r'                    if "GenerateRequestsPerDay".*?return LLMProviderError\(f"Gemini quota exhausted \(429\): \{e\}"\)', replacement, text, flags=re.DOTALL)

with open("backend/app/ai/providers/google.py", "w", encoding="utf-8") as f:
    f.write(text)
