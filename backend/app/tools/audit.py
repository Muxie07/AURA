import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ToolExecutionAudit
from app.tools.schemas import ToolContext, ToolDefinition, ToolResult


async def check_idempotency_key(
    db: AsyncSession, organization_id: uuid.UUID, idempotency_key: str
) -> ToolExecutionAudit | None:
    stmt = (
        select(ToolExecutionAudit)
        .where(
            ToolExecutionAudit.organization_id == organization_id,
            ToolExecutionAudit.idempotency_key == idempotency_key,
            ToolExecutionAudit.status == "succeeded",
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def persist_tool_audit(
    db: AsyncSession,
    context: ToolContext,
    definition: ToolDefinition,
    arguments: dict[str, Any],
    started_at: datetime,
    completed_at: datetime | None,
    duration_ms: int,
    result: ToolResult,
    input_hash: str,
    status: str = "succeeded",
    existing_audit_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Persist the tool execution to the database."""

    if existing_audit_id:
        stmt = (
            update(ToolExecutionAudit)
            .where(ToolExecutionAudit.id == existing_audit_id)
            .values(
                status=status,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_type=result.error_type,
                result_summary=str(result.message) if result.message else ("Success" if status == "succeeded" else "Failed")
            )
        )
        await db.execute(stmt)
        return existing_audit_id

    new_id = uuid.uuid4()
    audit = ToolExecutionAudit(
        id=new_id,
        organization_id=context.organization_id,
        agent_run_id=context.agent_run_id,
        execution_id=context.execution_id,
        tool_name=definition.name,
        tool_version="1.0",
        source=definition.source.value,
        risk_level=definition.risk_level.value,
        status=status,
        idempotency_key=context.idempotency_key,
        args_hash=input_hash,
        request_id=context.request_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        retry_count=0,
        error_type=result.error_type,
        error_code=None,
        result_summary=str(result.message)
        if result.message
        else ("Success" if status == "succeeded" else "Failed"),
    )
    db.add(audit)
    return new_id
