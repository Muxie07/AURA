"""
AURA Pydantic Schemas — Message.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.database.models import MessageRole
from app.schemas.common import AURABaseModel


class MessageCreate(AURABaseModel):
    """Request body for adding a message to a conversation."""

    role: MessageRole = Field(default=MessageRole.USER)
    content: str = Field(min_length=1, max_length=50_000)
    structured_content: dict[str, Any] | None = None


class MessageResponse(AURABaseModel):
    """Serialized message returned by the API."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    structured_content: dict[str, Any] | None
    agent_run_id: uuid.UUID | None
    token_count: int | None
    created_at: datetime
    updated_at: datetime
