import re

with open("backend/app/main.py", "r") as f:
    c = f.read()

# 1. Top-level imports
c = c.replace('from app.observability import RequestIDMiddleware, configure_logging, get_logger\n',
              'from app.observability import RequestIDMiddleware, RequestMetricsMiddleware, configure_logging, get_logger\nfrom starlette.middleware.base import BaseHTTPMiddleware\nfrom starlette.requests import Request\nfrom fastapi.responses import JSONResponse\nfrom fastapi.middleware.trustedhost import TrustedHostMiddleware\n')

# 2. Add Middlewares class definitions
middlewares_code = '''
class MaxSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes
        
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
'''


# 3. Replace lifespan
import_block = '''import asyncio
import os
from pathlib import Path
import sqlalchemy as sa
import alembic.command
import alembic.config

def upgrade_with_lock(cfg: alembic.config.Config) -> None:
    settings = get_settings()
    eng = sa.create_engine(settings.database_url_sync)
    with eng.connect() as conn:
        conn.execute(sa.text("SELECT pg_advisory_lock(727274)"))
        try:
            alembic.command.upgrade(cfg, "head")
        finally:
            conn.execute(sa.text("SELECT pg_advisory_unlock(727274)"))
            conn.commit()
'''
c = c.replace('if TYPE_CHECKING:', import_block + '\nif TYPE_CHECKING:')

old_lifespan = re.search(r'async def lifespan\(app: FastAPI.*?\n\ndef create_app', c, flags=re.DOTALL).group(0)
old_lifespan = old_lifespan[:-15]  # remove \n\ndef create_app

new_lifespan = '''async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging()
    logger = get_logger(__name__)

    logger.info("aura_starting", environment=settings.aura_env.value, debug=settings.aura_debug)

    if settings.aura_run_migrations_on_startup:
        logger.info("Running database migrations...")
        ini_path = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
        alembic_cfg = alembic.config.Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent.parent / "migrations"))
        await asyncio.to_thread(upgrade_with_lock, alembic_cfg)

    await initialize_database()

    from app.security.rate_limit import get_redis_client
    redis = await get_redis_client()
    try:
        await redis.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning(f"redis_connection_failed: {e}")

    from app.database.base import get_session_factory
    from app.database.models import AgentRun, AgentRunStatus
    from datetime import datetime, timedelta, UTC
    
    try:
        SessionFactory = get_session_factory()
        async with SessionFactory() as db:
            cutoff = datetime.now(UTC) - timedelta(seconds=settings.aura_agent_run_heartbeat_seconds * 3)
            await db.execute(
                sa.update(AgentRun)
                .where(
                    AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                    AgentRun.updated_at < cutoff
                )
                .values(
                    status=AgentRunStatus.FAILED,
                    error_message="Worker lease expired/crashed",
                    updated_at=datetime.now(UTC)
                )
            )
            await db.commit()
            logger.info("stuck_run_recovery_complete")
    except Exception as e:
        logger.error("stuck_run_recovery_failed", error=str(e))

    from app.tools.registry import ToolRegistry
    registry = ToolRegistry()
    app.state.tool_registry = registry

    yield

    logger.info("aura_shutting_down")
    grace = os.getenv("AURA_SHUTDOWN_GRACE_SECONDS", "5")
    logger.info(f"waiting {grace}s for in-flight requests")
    await asyncio.sleep(float(grace))
    await close_database()
    logger.info("aura_shutdown_complete")
'''
c = c.replace(old_lifespan, new_lifespan)

# 4. Middleware Ordering
old_middlewares = re.search(r'    # CORS.*?app\.add_middleware\(RequestIDMiddleware\)', c, flags=re.DOTALL).group(0)

new_middlewares = '''    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.aura_trusted_hosts
    )
    app.add_middleware(
        MaxSizeMiddleware, 
        max_bytes=settings.aura_max_request_bytes
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)

    if settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://your-production-domain.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID", "X-Correlation-ID"]
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Correlation-ID"]
        )'''
c = c.replace(old_middlewares, new_middlewares)

# 5. Add /ready route
ready_route = '''
    @app.get("/ready", tags=["health"])
    async def readiness_check():
        """Detailed readiness probe (DB, Redis, Migrations)."""
        settings = get_settings()
        from app.database.base import get_session_factory
        from app.security.rate_limit import get_redis_client
        import sqlalchemy as sa
        from fastapi import HTTPException
        status = {"db": "ok", "redis": "ok"}
        ready = True
        try:
            SessionFactory = get_session_factory()
            async with SessionFactory() as db:
                await db.execute(sa.text("SELECT 1"))
        except Exception:
            status["db"] = "failed"
            ready = False
            
        try:
            redis = await get_redis_client()
            await redis.ping()
        except Exception:
            status["redis"] = "failed"
            ready = False
            
        if not ready:
            raise HTTPException(status_code=503, detail=status)
        return status

    app.include_router(api_v1_router)'''
c = c.replace('    app.include_router(api_v1_router)', ready_route)

# Write back
c = c.replace('def create_app() -> FastAPI:', middlewares_code + '\n\ndef create_app() -> FastAPI:')

with open("backend/app/main.py", "w") as f:
    f.write(c)
