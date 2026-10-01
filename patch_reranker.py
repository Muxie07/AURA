import os

with open("backend/app/knowledge/reranking.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("MockReranker", "FallbackReranker")
text = text.replace("Mock reranker for testing", "Deterministic fallback reranker (identity pass-through)")

with open("backend/app/knowledge/reranking.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("backend/app/knowledge/rag_service.py", "r", encoding="utf-8") as f:
    text2 = f.read()
text2 = text2.replace("MockReranker", "FallbackReranker")
with open("backend/app/knowledge/rag_service.py", "w", encoding="utf-8") as f:
    f.write(text2)

print("Renamed reranker!")
