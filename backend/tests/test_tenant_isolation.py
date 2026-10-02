import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Organization, User


@pytest.mark.asyncio
async def test_tenant_isolation_api(client: AsyncClient, db_session: AsyncSession, organization: Organization, user: User):
    """Test that users cannot access resources belonging to other tenants."""
    # Create a second organization and user
    org2 = Organization(
        id=uuid.uuid4(),
        name="Evil Corp",
        slug="evil-corp",
        is_active=True,
        settings={}
    )
    user2 = User(
        id=uuid.uuid4(),
        organization_id=org2.id,
        email="hacker@evil.com",
        full_name="Evil User",
        is_active=True,
        is_superuser=False,
        metadata_={}
    )
    db_session.add_all([org2, user2])
    await db_session.commit()

    # The `client` fixture is authenticated as `user` (org 1).
    # We will try to pass the org2 ID in the headers to see if we can spoof it.

    # Try fetching users for org2
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    # Let's mock a request to an org-scoped endpoint if it existed
    # For now, just ensure the headers spoofing on the MCP route fails
    response = await client.get(
        "/api/v1/mcp",
        headers={"X-Organization-Id": str(org2.id)}
    )
    # The client fixture uses user token, token has org1. Header is org2.
    # auth_middleware in routes.py should return 403 Spoofed organization header
    assert response.status_code == 403
    assert b"Spoofed organization header" in response.content

@pytest.mark.asyncio
async def test_mcp_auth_missing(app):
    """Test that MCP endpoint rejects unauthenticated requests."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as unauth_client:
        response = await unauth_client.get("/api/v1/mcp")
        assert response.status_code == 401
        assert b"Unauthorized" in response.content
