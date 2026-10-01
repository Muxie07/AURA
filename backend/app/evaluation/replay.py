"""
AURA Phase 9 — Replay Engine.

Allows deterministic replay of agent runs using recorded inputs.
Supports run export to JSON for debugging and auditing.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# In-memory replay store — keyed by org_id + run_id
_replay_store: dict[str, dict[str, Any]] = {}


class ReplayEngine:
    """
    Records agent run configurations for deterministic replay.
    All data is stored with tenant isolation.
    """

    @staticmethod
    def record(
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
        request: str,
        model: str,
        plan: dict[str, Any] | None = None,
        action_history: list[dict[str, Any]] | None = None,
        retrieved_context: list[dict[str, Any]] | None = None,
        final_response: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a run's configuration for potential replay."""
        key = f"{organization_id}:{run_id}"
        _replay_store[key] = {
            "run_id": str(run_id),
            "organization_id": str(organization_id),
            "recorded_at": datetime.now(UTC).isoformat(),
            "request": request,
            "model": model,
            "plan": plan,
            "action_history": action_history or [],
            "retrieved_context": retrieved_context or [],
            "final_response": final_response,
            "metadata": metadata or {},
        }
        logger.info("replay_recorded", run_id=str(run_id), org=str(organization_id))

    @staticmethod
    def get(
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Retrieve a recorded run — tenant isolated."""
        key = f"{organization_id}:{run_id}"
        record = _replay_store.get(key)
        if not record:
            return None
        # Verify tenant ownership
        if record["organization_id"] != str(organization_id):
            logger.warning(
                "replay_tenant_violation",
                requested_org=str(organization_id),
                stored_org=record["organization_id"],
            )
            return None
        return record

    @staticmethod
    def export_json(
        organization_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> str | None:
        """Export a recorded run as JSON — tenant isolated."""
        record = ReplayEngine.get(organization_id, run_id)
        if not record:
            return None
        return json.dumps(record, indent=2, default=str)

    @staticmethod
    def list_org_runs(organization_id: uuid.UUID) -> list[str]:
        """List all recorded run IDs for an organization."""
        prefix = f"{organization_id}:"
        return [
            key.split(":", 1)[1]
            for key in _replay_store
            if key.startswith(prefix)
        ]

    @staticmethod
    def clear(organization_id: uuid.UUID | None = None) -> None:
        """Clear replay store (for testing)."""
        if organization_id:
            prefix = f"{organization_id}:"
            keys_to_delete = [k for k in _replay_store if k.startswith(prefix)]
            for k in keys_to_delete:
                del _replay_store[k]
        else:
            _replay_store.clear()
