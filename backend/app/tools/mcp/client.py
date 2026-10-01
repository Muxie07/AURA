import json
import uuid
from contextlib import AsyncExitStack
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
    def __init__(self, url: str, organization_id: uuid.UUID | str):
        self.url = url
        self.organization_id = str(organization_id)
        self.exit_stack = AsyncExitStack()
        self.session = None
        self.http_client = None

    async def connect(self):
        from datetime import datetime, timedelta

        import jwt

        from app.config.settings import get_settings

        settings = get_settings()

        # Create a valid service token for MCP
        payload = {
            "sub": "mcp-service",
            "org_id": self.organization_id,
            "permissions": ["tools:read", "tools:write", "tools:external"],
            "exp": datetime.utcnow() + timedelta(minutes=10),
        }
        token = jwt.encode(payload, settings.aura_secret_key.get_secret_value(), algorithm="HS256")

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": self.organization_id,
            "X-MCP-Permissions": "tools:read,tools:write,tools:external",
        }

        transport = await self.exit_stack.enter_async_context(
            sse_client(self.url, headers=headers, timeout=30.0)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(transport[0], transport[1])
        )
        await self.session.initialize()

    async def close(self):
        await self.exit_stack.aclose()
        if self.http_client:
            await self.http_client.aclose()
