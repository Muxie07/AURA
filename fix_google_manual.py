with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith("from app.ai.errors.exceptions import LLMProviderError, LLMTimeoutError"):
        new_lines.append("from app.ai.errors.exceptions import (\n    LLMAuthenticationError,\n    LLMProviderError,\n    LLMRateLimitError,\n    LLMTimeoutError,\n    LLMQuotaExceededError\n)\n")
        skip = True
        continue
    
    if skip:
        if line.strip() == ")":
            skip = False
        continue
        
    new_lines.append(line)

with open("backend/app/ai/providers/google.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
