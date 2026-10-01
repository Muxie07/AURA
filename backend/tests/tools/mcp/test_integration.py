import uuid

import httpx2
import pytest
from httpx2 import ASGITransport

from app.mcp_main import app
from app.tools.mcp.client import MCPClientManager, discover_mcp_tools


@pytest.mark.asyncio
@pytest.mark.skip(reason="BLOCKED - ENVIRONMENT: Docker unavailable")
async def test_mcp_client_discovery_and_execution(monkeypatch):
    org_id = uuid.uuid4()

    original_async_client = httpx2.AsyncClient

    def mock_async_client(*args, **kwargs):
        kwargs['transport'] = ASGITransport(app=app)
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr("app.tools.mcp.client.httpx2.AsyncClient", mock_async_client)

    # Use the real running HTTP server
    manager = MCPClientManager("http://127.0.0.1:8000/api/v1/mcp/", str(org_id))
    await manager.connect()

    # Prove negotiated version
    assert getattr(manager.session, "protocol_version", None) is not None, "Protocol version not negotiated"

    # Discover tools
    tools = await discover_mcp_tools(manager.session)
    assert len(tools) > 0
    names = [t.definition.name for t in tools]
    assert "mcp.customer.search" in names

    # Get executor
    executor = next(t for t in tools if t.definition.name == "mcp.customer.search")

    # Execute tool
    from app.tools.schemas import ToolContext
    context = ToolContext(
        organization_id=org_id,
        agent_run_id=uuid.uuid4(),
        execution_id="test-exec-1"
    )

    result = await executor.execute({"query": "Test"}, context)
    assert result.status == "succeeded"
    assert "customers" in result.result

    await manager.close()
