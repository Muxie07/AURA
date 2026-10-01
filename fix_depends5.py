import io
with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from fastapi import Depends\n", "")
content = content.replace("from __future__ import annotations\n", "from __future__ import annotations\nfrom fastapi import Depends\n")

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
