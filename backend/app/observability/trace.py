import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentTraceEvent


class AgentTracer:
    """
    Records deterministic execution traces for the agent to ensure observability.
    """
    def __init__(self, db: AsyncSession, run_id: uuid.UUID, organization_id: uuid.UUID):
        self.db = db
        self.run_id = run_id
        self.organization_id = organization_id
        self.sequence = 0

    async def record_event(
        self,
        event_type: str,
        component: str,
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None
    ):
        self.sequence += 1
        event = AgentTraceEvent(
            organization_id=self.organization_id,
            run_id=self.run_id,
            sequence=self.sequence,
            event_type=event_type,
            component=component,
            metadata_=metadata,
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC)
        )
        self.db.add(event)
        # We don't commit immediately for every event to save I/O overhead.
        # But for critical events we might want to flush.
        await self.db.flush()
