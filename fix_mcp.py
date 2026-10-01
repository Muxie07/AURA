with open("backend/app/main.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

mount_code = """
    app.include_router(api_v1_router)
    
    from app.tools.mcp.routes import asgi_sse
    app.mount("/api/v1/mcp", asgi_sse)
"""

text = text.replace("app.include_router(api_v1_router)", mount_code.strip())

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(text)
