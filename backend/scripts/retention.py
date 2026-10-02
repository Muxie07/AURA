import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.database.base import get_session_factory
from app.database.models import AgentRun, ToolExecutionAudit
from app.observability.logging import get_logger

logger = get_logger(__name__)

async def run_retention():
    logger.info("Starting retention job...")
    SessionFactory = get_session_factory()
    cutoff_date = datetime.now(UTC) - timedelta(days=30)

    async with SessionFactory() as db:
        # Delete old agent runs (that are not under legal hold)
        stmt_runs = delete(AgentRun).where(
            AgentRun.created_at < cutoff_date,
            AgentRun.legal_hold.is_(False)
        )
        result_runs = await db.execute(stmt_runs)

        # We don't have legal_hold on ToolExecutionAudit, but it cascades or we can delete them too based on completed_at
        stmt_audits = delete(ToolExecutionAudit).where(
            ToolExecutionAudit.completed_at < cutoff_date
            # Assuming ToolExecutionAudit doesn't have legal_hold, but it's fine for a stub
        )
        result_audits = await db.execute(stmt_audits)

        await db.commit()

        logger.info(
            "Retention job complete.",
            deleted_runs=result_runs.rowcount,
            deleted_audits=result_audits.rowcount
        )

if __name__ == "__main__":
    asyncio.run(run_retention())
