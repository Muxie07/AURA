import pytest

from app.tools.mcp.client import MCPClientManager


@pytest.mark.asyncio
async def test_mcp_client_manager_sanitizes_descriptions():
    manager = MCPClientManager()

    # We will mock the ClientSession list_tools response
    class MockTool:
        def __init__(self, name, description, schema):
            self.name = name
            self.description = description
            self.inputSchema = schema

    class MockResult:
        def __init__(self, tools):
            self.tools = tools

    class MockSession:
        async def list_tools(self):
            long_desc = "A" * 600
            schema = {
                "type": "object",
                "properties": {
                    "__aura_context": {"type": "string"},
                    "valid_arg": {"type": "string"}
                }
            }
            return MockResult([MockTool("test_tool", long_desc, schema)])

    # Mock the get_session to return our MockSession
    async def mock_get_session(url, org_id):
        return MockSession()

    manager.get_session = mock_get_session

    executors = await manager.discover_tools("http://fake", "fake_org")
    assert len(executors) == 1

    defn = executors[0].definition
    assert defn.name == "mcp.test_tool"
    assert len(defn.description) == 500
    assert defn.description.endswith("...")
    assert "__aura_context" not in defn.input_schema["properties"]
    assert "valid_arg" in defn.input_schema["properties"]
