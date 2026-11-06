import uuid
from typing import ClassVar

import structlog
from arq.connections import RedisSettings

from app.agents.services.agent_service import AgentWorkflowService
from app.ai.services.llm import LLMService
from app.config.settings import get_settings
from app.database.base import get_session_factory
from app.database.models import AgentRun
from app.knowledge.rag_service import RAGService
from app.tools.mcp.client import MCPClientManager

logger = structlog.get_logger(__name__)

async def startup(ctx):
    logger.info("Worker starting up")
    settings = get_settings()
    from app.database.base import initialize_database
    await initialize_database()
    ctx["session_factory"] = get_session_factory()

    ctx["mcp_manager"] = MCPClientManager()
    ctx["llm"] = LLMService()
    ctx["settings"] = settings

async def shutdown(ctx):
    logger.info("Worker shutting down")
    await ctx["mcp_manager"].close()

async def run_agent(ctx, run_id_str: str):
    run_id = uuid.UUID(run_id_str)

    import structlog
    structlog.contextvars.clear_contextvars()
    trace_id = f"worker_{uuid.uuid4().hex[:12]}"
    structlog.contextvars.bind_contextvars(
        run_id=str(run_id),
        trace_id=trace_id,
        request_id=trace_id,
    )

    session_factory = ctx["session_factory"]
    llm = ctx["llm"]

    async with session_factory() as db:
        run = await db.scalar(
            __import__('sqlalchemy').select(AgentRun).where(AgentRun.id == run_id)
        )
        if not run:
            logger.error("AgentRun not found", run_id=str(run_id))
            return

        org_id = run.organization_id

        rag = RAGService(db, llm)
        agent_service = AgentWorkflowService(db, llm, rag, mcp_manager=ctx.get("mcp_manager"))

        await agent_service.initialize(org_id)
        try:
            await agent_service.execute_run(run_id)
        finally:
            await agent_service.aclose()


# Load settings here so WorkerSettings class property can read it
try:
    _settings = get_settings()
    _redis_url = _settings.redis_url
except Exception:
    _redis_url = 'redis://redis:6379/0'


class WorkerSettings:
    functions: ClassVar[list] = [run_agent]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_redis_url)
