"""
AURA Pydantic Schemas — AgentRun.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from app.schemas.common import AURABaseModel

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from app.database.models import AgentRunStatus


class AgentRunCreate(AURABaseModel):
    """Internal schema for creating an agent run."""

    conversation_id: uuid.UUID
    user_id: uuid.UUID
    user_request: str = Field(min_length=1, max_length=50_000)


class AgentRunResponse(AURABaseModel):
    """Serialized agent run returned by the API."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    status: AgentRunStatus
    user_request: str
    intent_analysis: dict[str, Any] | None
    plan: dict[str, Any] | None
    final_response: str | None
    error_message: str | None
    iteration_count: int
    total_tokens_input: int
    total_tokens_output: int
    estimated_cost_usd: float | None
    latency_ms: int | None
    model_provider: str | None
    model_name: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
