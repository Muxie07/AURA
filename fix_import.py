import io
with io.open("backend/app/api/v1/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import asyncio, Depends, HTTPException", "import asyncio\nfrom fastapi import Depends, HTTPException")
with io.open("backend/app/api/v1/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
