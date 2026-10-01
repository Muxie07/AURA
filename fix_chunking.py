import io
import re

with io.open("backend/app/knowledge/chunking.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("good_splits = []", "good_splits: list[str] = []")
content = content.replace("current_chunk = []", "current_chunk: list[str] = []")
content = content.replace("overlap_chunk = []", "overlap_chunk: list[str] = []")

with io.open("backend/app/knowledge/chunking.py", "w", encoding="utf-8") as f:
    f.write(content)
