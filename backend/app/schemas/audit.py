"""
AURA Pydantic Schemas — Audit Events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.schemas.common import AURABaseModel

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from app.database.models import AuditEventType


class AuditEventResponse(AURABaseModel):
    """Serialized audit event returned by the API."""

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    agent_run_id: uuid.UUID | None
    event_type: AuditEventType
    event_data: dict[str, Any]
    request_id: str | None
    ip_address: str | None
    created_at: datetime
