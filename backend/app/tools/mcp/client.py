import json
from contextlib import AsyncExitStack
from datetime import UTC
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from app.tools.errors import ToolExecutionError
from app.tools.executor import BaseToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult, ToolSource


class MCPToolExecutor(BaseToolExecutor):
    def __init__(self, definition: ToolDefinition, session: ClientSession, mcp_name: str):
        super().__init__(definition)
        self.session = session
        self.mcp_name = mcp_name

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        if context.dry_run:
            arguments["_dry_run"] = True
        if context.idempotency_key:
            arguments["_idempotency_key"] = context.idempotency_key

        try:
            # We call the real MCP tool name, NOT the prefixed one
            result = await self.session.call_tool(self.mcp_name, arguments=arguments)
            if not result.content:
                return ToolResult(
                    status="failed", message="No content returned from MCP", retryable=False
                )

            if not hasattr(result.content[0], "text"):
                return ToolResult(
                    status="failed", message="MCP returned non-text content", retryable=False
                )
            text = result.content[0].text
            if text.startswith("Error:"):
                return ToolResult(status="failed", message=text, retryable=False)

            data = json.loads(text)
            return ToolResult(status="succeeded", result=data)
        except Exception as e:
            raise ToolExecutionError(f"MCP execution failed: {e}") from e


async def discover_mcp_tools(session: ClientSession) -> list[BaseToolExecutor]:
    result = await session.list_tools()
    executors: list[BaseToolExecutor] = []
    for tool in result.tools:
        risk = RiskLevel.READ
        if "create" in tool.name or "update" in tool.name or "delete" in tool.name:
            risk = RiskLevel.WRITE

        defn = ToolDefinition(
            name=f"mcp.{tool.name}",
            description=tool.description or "",
            input_schema=tool.inputSchema,
            risk_level=risk,
            source=ToolSource.MCP,
        )
        # Pass the original tool name to the executor
        executors.append(MCPToolExecutor(defn, session, tool.name))
    return executors


class MCPClientManager:
    """Manages long-lived MCP connections per server/org."""
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions = {}  # key: (url, org_id), value: ClientSession
        self.tool_cache = {} # key: (url, org_id), value: list[BaseToolExecutor]

    async def get_session(self, url: str, organization_id: str) -> ClientSession:
        key = (url, str(organization_id))
        if key in self.sessions:
            return self.sessions[key]

        from datetime import datetime, timedelta

        import jwt

        from app.config.settings import get_settings
        settings = get_settings()

        payload = {
            "sub": "mcp-service",
            "org_id": str(organization_id),
            "permissions": ["tools:read", "tools:write", "tools:external"],
            "exp": datetime.now(UTC) + timedelta(days=1),
        }
        token = jwt.encode(payload, settings.aura_secret_key.get_secret_value(), algorithm="HS256")
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(organization_id),
            "X-MCP-Permissions": "tools:read,tools:write,tools:external",
        }

        # Per-server timeout
        transport = await self.exit_stack.enter_async_context(
            sse_client(url, headers=headers, timeout=10.0)
        )
        session = await self.exit_stack.enter_async_context(
            ClientSession(transport[0], transport[1])
        )
        await session.initialize()
        self.sessions[key] = session
        return session

    async def discover_tools(self, url: str, organization_id: str) -> list[BaseToolExecutor]:
        key = (url, str(organization_id))
        session = await self.get_session(url, organization_id)
        # Client side poisoning mitigation: sanitize descriptions, cap length
        result = await session.list_tools()
        executors = []
        for tool in result.tools:
            risk = RiskLevel.READ
            if "create" in tool.name or "update" in tool.name or "delete" in tool.name:
                risk = RiskLevel.WRITE

            desc = tool.description or ""
            if len(desc) > 500:
                desc = desc[:497] + "..."

            # Remove __aura_context if provided by untrusted server
            schema = dict(tool.inputSchema) if tool.inputSchema else {}
            if "properties" in schema and "__aura_context" in schema["properties"]:
                del schema["properties"]["__aura_context"]

            defn = ToolDefinition(
                name=f"mcp.{tool.name}",
                description=desc,
                input_schema=schema,
                risk_level=risk,
                source=ToolSource.MCP,
            )
            executors.append(MCPToolExecutor(defn, session, tool.name))

        self.tool_cache[key] = executors
        return executors

    async def close(self):
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.tool_cache.clear()
