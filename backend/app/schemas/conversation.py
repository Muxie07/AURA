"""
AURA Pydantic Schemas — Conversation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.database.models import ConversationStatus
from app.schemas.common import AURABaseModel


class ConversationCreate(AURABaseModel):
    """Request body for creating a new conversation."""

    title: str | None = Field(
        default=None,
        max_length=500,
        description="Optional conversation title. Auto-generated if omitted.",
    )
    initial_message: str | None = Field(
        default=None,
        max_length=10_000,
        description="Optional first user message to start the conversation.",
    )


class ConversationUpdate(AURABaseModel):
    """Request body for updating a conversation."""

    title: str | None = Field(default=None, max_length=500)
    status: ConversationStatus | None = None


class ConversationResponse(AURABaseModel):
    """Serialized conversation returned by the API."""

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(default=0, description="Number of messages in this conversation.")
