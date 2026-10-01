import io
import re
with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from fastapi import APIRouter, HTTPException, Query, status", "from fastapi import APIRouter, HTTPException, Query, status, Depends")

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
