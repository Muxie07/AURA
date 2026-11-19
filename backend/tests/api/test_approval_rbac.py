"""RBAC regression: only OWNER/ADMIN may approve or reject HITL requests.

Exercises the real auth path (JWT -> DB user lookup -> RequireRole), so the
role check fires before any approval lookup; a random approval id is enough.
"""

import uuid

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
