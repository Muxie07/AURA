"""
AURA API v1 - Router.

Aggregates all v1 endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.eval import router as eval_router
from app.api.v1.forecasting import router as forecasting_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.runs import router as runs_router
from app.api.v1.settings import router as settings_router
from app.tools.mcp.routes import mcp_router

api_v1_router = APIRouter(prefix="/api/v1")

# Register sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(runs_router)
api_v1_router.include_router(eval_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(forecasting_router)

# The MCP router paths already contain /api/v1 prefix due to how SSE transport is constructed,
# so we attach it to the root app or we strip the prefix here.
# Actually SseServerTransport binds strictly to the path, so we should just attach it without prefix to api_v1_router
# Wait, SseServerTransport takes a full URL path. I will just include it.
api_v1_router.include_router(mcp_router)
