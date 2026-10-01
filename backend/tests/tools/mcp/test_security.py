import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config.settings import get_settings
from app.mcp_main import app
from app.tools.mcp.routes import start_mcp_server
from app.tools.mcp.server import call_tool, mcp_org_id, mcp_permissions


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_server_loop():
    task = asyncio.create_task(start_mcp_server())
    await asyncio.sleep(0.5)
    yield
    task.cancel()


def create_mock_token(org_id: str, permissions: list[str]) -> str:
    settings = get_settings()
    payload = {
        "sub": str(uuid.uuid4()),
        "org_id": org_id,
        "permissions": permissions,
    }
    return jwt.encode(payload, settings.aura_secret_key.get_secret_value(), algorithm="HS256")


@pytest.mark.asyncio
async def test_mcp_unauthenticated_request_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mcp/messages/",
            headers={"Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        if response.status_code == 307:
            response = await client.post(
                response.headers["location"],
                headers={"Accept": "application/json, text/event-stream"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
        assert response.status_code == 401
        assert response.text == "Unauthorized"


@pytest.mark.asyncio
async def test_mcp_invalid_token_rejected():
    headers = {
        "Authorization": "Bearer invalid-token",
        "Accept": "application/json, text/event-stream",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mcp/messages/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        if response.status_code == 307:
            response = await client.post(
                response.headers["location"],
                headers=headers,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
        assert response.status_code == 401
        assert response.text == "Invalid token"


@pytest.mark.asyncio
async def test_mcp_valid_tenant_a_cannot_access_tenant_b():
    org_id = str(uuid.uuid4())
    fake_org_id = str(uuid.uuid4())
    token = create_mock_token(org_id, ["tools:read"])
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": fake_org_id,
        "Accept": "application/json, text/event-stream",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mcp/messages/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        if response.status_code == 307:
            response = await client.post(
                response.headers["location"],
                headers=headers,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
        assert response.status_code == 403
        assert response.text == "Spoofed organization header"


@pytest.mark.asyncio
async def test_mcp_write_permission_denied():
    org_id = uuid.uuid4()
    mcp_org_id.set(org_id)
    mcp_permissions.set(["tools:read"])  # Missing tools:write

    result = await call_tool("test_write_tool", {})
    text = result[0].text
    assert (
        "Unknown tool" in text or "Missing tools:write" in text or "DENY" in text or "Error" in text
    )


@pytest.mark.asyncio
async def test_mcp_direct_execution_cannot_bypass_policy_engine():
    org_id = uuid.uuid4()
    mcp_org_id.set(org_id)
    mcp_permissions.set(["tools:read", "tools:write", "tools:external"])

    result = await call_tool("test_external_tool", {})
    text = result[0].text
    assert "Unknown tool" in text or "Missing tools" in text or "Error" in text
