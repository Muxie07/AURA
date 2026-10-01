path = "backend/app/ai/providers/heuristic.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("from app.ai.providers.base import Usage", "")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed Usage import")
