from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.database.base import close_database as dispose_database
from app.database.base import initialize_database
from app.tools.mcp.routes import asgi_sse, mcp_router, start_mcp_server

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    await initialize_database()
    mcp_task = asyncio.create_task(start_mcp_server())
    yield
    mcp_task.cancel()
    await dispose_database()

app = FastAPI(title="AURA MCP Server", lifespan=lifespan)

# Add route
app.include_router(mcp_router, prefix="/api/v1")
app.mount("/api/v1/mcp/messages", asgi_sse)

@app.get("/health")
async def health():
    return {"status": "ok"}
