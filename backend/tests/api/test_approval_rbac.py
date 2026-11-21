"""RBAC regression: only OWNER/ADMIN may approve or reject HITL requests.

Exercises the real auth path (JWT -> DB user lookup -> RequireRole), so the
role check fires before any approval lookup; a random approval id is enough.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, UserRole


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.VIEWER, UserRole.MEMBER])
@pytest.mark.parametrize("action", ["approve", "reject"])
async def test_non_admin_cannot_action_approvals(
    client: AsyncClient, db_session: AsyncSession, user: User, role: UserRole, action: str
) -> None:
    user.role = role
    await db_session.flush()

    response = await client.post(f"/api/v1/approvals/{uuid.uuid4()}/{action}")

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.OWNER, UserRole.ADMIN])
async def test_admin_passes_role_check(
    client: AsyncClient, db_session: AsyncSession, user: User, role: UserRole
) -> None:
    user.role = role
    await db_session.flush()

    response = await client.post(f"/api/v1/approvals/{uuid.uuid4()}/approve")

    # Past the role gate, a nonexistent approval is a 404 — not a 403.
    assert response.status_code == 404, response.text


async def _pending_approval_from_other_user(db_session: AsyncSession, org_id: uuid.UUID):
    from app.database.models import (
        AgentRun,
        AgentRunStatus,
        ApprovalRequest,
        ApprovalStatus,
        Conversation,
        ConversationStatus,
    )

    initiator = User(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=f"initiator-{uuid.uuid4().hex[:6]}@example.com",
        full_name="Initiator",
        is_active=True,
        metadata_={},
    )
    db_session.add(initiator)
    await db_session.flush()
    conv = Conversation(
        organization_id=org_id,
        user_id=initiator.id,
        title="approval flow",
        status=ConversationStatus.ACTIVE,
        metadata_={},
    )
    db_session.add(conv)
    await db_session.flush()
    run = AgentRun(
        organization_id=org_id,
        conversation_id=conv.id,
        user_id=initiator.id,
        user_request="send quotation",
        status=AgentRunStatus.AWAITING_APPROVAL,
    )
    db_session.add(run)
    await db_session.flush()
    approval = ApprovalRequest(
        agent_run_id=run.id,
        organization_id=org_id,
        tool_name="communication.send_quotation",
        action_summary="Send quotation",
        action_details={},
        args_hash="0" * 64,
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.flush()
    return approval


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_status"), [("approve", "approved"), ("reject", "denied")]
)
async def test_admin_can_action_pending_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    expected_status: str,
) -> None:
    """End-to-end through the real endpoint (regression: missing UTC import -> 500)."""
    import app.api.v1.runs as runs_module

    async def _no_resume(_run_id: uuid.UUID) -> None:
        return None

    monkeypatch.setattr(runs_module, "run_agent_in_background", _no_resume)
    user.role = UserRole.ADMIN
    approval = await _pending_approval_from_other_user(db_session, user.organization_id)

    response = await client.post(f"/api/v1/approvals/{approval.id}/{action}")

    assert response.status_code == 200, response.text
    await db_session.refresh(approval)
    assert approval.status.value == expected_status
    assert approval.actioned_at is not None
    assert approval.actioned_by_id == user.id
