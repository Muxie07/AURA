import uuid

import pytest

from app.tools.mcp.server import call_tool, mcp_org_id, mcp_permissions


@pytest.mark.asyncio
async def test_mcp_tenant_isolation_unauthenticated(client):
    # Calling the tool without context
    # Ensure contextvars are empty
    # By default in a new task they should be empty if not set
    result = await call_tool("customer.search", {"query": "test"})
    assert result[0].text == "Error: Unauthenticated. Missing organization context."

@pytest.mark.asyncio
async def test_mcp_tenant_isolation_authenticated(client):
    org_id = uuid.uuid4()
    # Mock the ASGI contextvar middleware behavior
    mcp_org_id.set(org_id)
    mcp_permissions.set(["tools:read", "tools:write", "tools:external"])

    # Notice we pass NO __aura_context here, because the server reads from connection-level contextvar
    result = await call_tool("customer.search", {"query": "test"})
    # The result should be valid json or empty array, not an auth error
    assert "Error:" not in result[0].text

@pytest.mark.asyncio
async def test_mcp_authorization_failure(client):
    org_id = uuid.uuid4()
    mcp_org_id.set(org_id)
    mcp_permissions.set(["tools:read"]) # Missing write

    result = await call_tool("quotation.create_draft", {"quantity": 10})
    assert "Missing tools:write permission" in result[0].text

@pytest.mark.asyncio
async def test_mcp_anti_spoofing(client):
    org_id = uuid.uuid4()
    fake_org_id = uuid.uuid4()

    mcp_org_id.set(org_id)
    mcp_permissions.set(["tools:read"])

    # Attempt to spoof tenant ID in arguments
    result = await call_tool(
        "customer.search",
        {
            "query": "test",
            "organization_id": str(fake_org_id),
            "__aura_context": {"organization_id": str(fake_org_id)}
        }
    )
    # The server drops the spoofed arguments and relies purely on `mcp_org_id.get()`
    assert "Error:" not in result[0].text
