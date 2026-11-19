"""
AURA API v1 - Router.

Aggregates all v1 endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.ai import router as ai_router
from app.api.v1.audit_api import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.eval import router as eval_router
from app.api.v1.forecasting import router as forecasting_router
from app.api.v1.gmail import router as gmail_router
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.mcp_hub import router as mcp_hub_router
from app.api.v1.models_api import router as models_router
from app.api.v1.runs import router as runs_router
from app.api.v1.settings import router as settings_router
from app.api.v1.tenants_api import router as tenants_router
from app.api.v1.tools import router as tools_router
from app.api.v1.workflows_api import router as workflows_router
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
api_v1_router.include_router(gmail_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(workflows_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(mcp_hub_router)
api_v1_router.include_router(models_router)

# The MCP SSE transport router
api_v1_router.include_router(mcp_router)
api_v1_router.include_router(tools_router)
