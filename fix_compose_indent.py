with open("docker-compose.yml", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("        PRIMARY_LLM_PROVIDER: google\n          FALLBACK_LLM_PROVIDER: google", "        PRIMARY_LLM_PROVIDER: google\n        FALLBACK_LLM_PROVIDER: google")
text = text.replace("        PRIMARY_LLM_MODEL: gemini-1.5-flash\n          FALLBACK_LLM_MODEL: gemini-2.5-flash-lite", "        PRIMARY_LLM_MODEL: gemini-1.5-flash\n        FALLBACK_LLM_MODEL: gemini-2.5-flash-lite")

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(text)
