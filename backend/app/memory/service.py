import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentMemory, MemoryScope


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_memory(
        self,
        organization_id: uuid.UUID,
        scope: MemoryScope,
        key: str,
        conversation_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
    ) -> dict[str, Any] | None:
        stmt = select(AgentMemory).where(
            AgentMemory.organization_id == organization_id,
            AgentMemory.scope == scope,
            AgentMemory.key == key,
        )
        if conversation_id:
            stmt = stmt.where(AgentMemory.conversation_id == conversation_id)
        if run_id:
            stmt = stmt.where(AgentMemory.run_id == run_id)

        result = await self.db.execute(stmt)
        mem = result.scalars().first()

        if not mem:
            return None

        if mem.expires_at and mem.expires_at < datetime.now(UTC):
            await self.delete_memory(organization_id, scope, key, conversation_id, run_id)
            return None

        return mem.content

    async def set_memory(
        self,
        organization_id: uuid.UUID,
        scope: MemoryScope,
        key: str,
        content: dict[str, Any],
        conversation_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        # Check existing
        stmt = select(AgentMemory).where(
            AgentMemory.organization_id == organization_id,
            AgentMemory.scope == scope,
            AgentMemory.key == key,
        )
        if conversation_id:
            stmt = stmt.where(AgentMemory.conversation_id == conversation_id)
        if run_id:
            stmt = stmt.where(AgentMemory.run_id == run_id)

        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing:
            existing.content = content
            existing.expires_at = expires_at
        else:
            mem = AgentMemory(
                organization_id=organization_id,
                conversation_id=conversation_id,
                run_id=run_id,
                scope=scope,
                key=key,
                content=content,
                expires_at=expires_at,
            )
            self.db.add(mem)

        await self.db.flush()

    async def delete_memory(
        self,
        organization_id: uuid.UUID,
        scope: MemoryScope,
        key: str,
        conversation_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
    ) -> None:
        stmt = delete(AgentMemory).where(
            AgentMemory.organization_id == organization_id,
            AgentMemory.scope == scope,
            AgentMemory.key == key,
        )
        if conversation_id:
            stmt = stmt.where(AgentMemory.conversation_id == conversation_id)
        if run_id:
            stmt = stmt.where(AgentMemory.run_id == run_id)

        await self.db.execute(stmt)
        await self.db.flush()
