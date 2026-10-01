with open("docker-compose.yml", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("FALLBACK_LLM_PROVIDER: google", "FALLBACK_LLM_PROVIDER: heuristic")
text = text.replace("FALLBACK_LLM_MODEL: gemini-3.5-flash-lite", "FALLBACK_LLM_MODEL: heuristic-fallback")

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated docker-compose.yml")
