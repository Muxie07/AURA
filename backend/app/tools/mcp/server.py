import json
import uuid
from contextvars import ContextVar

from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)

from app.tools.builtin import register_builtin_tools
from app.tools.registry import ToolRegistry
from app.tools.schemas import RiskLevel, ToolContext

mcp_registry = ToolRegistry()
register_builtin_tools(mcp_registry)

mcp_server = Server("aura-business-mcp")

# Context vars set by the FastAPI dependency
mcp_org_id: ContextVar[uuid.UUID] = ContextVar("mcp_org_id")
mcp_permissions: ContextVar[list[str]] = ContextVar("mcp_permissions")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    allowed = {"customer.search", "product.search", "pricing.get", "quotation.create_draft"}
    for defn in mcp_registry.list_definitions():
        if defn.name in allowed:
            # Drop the __aura_context from schema so LLM doesn't see it (if it's there)
            schema = dict(defn.input_schema)
            if "properties" in schema and "__aura_context" in schema["properties"]:
                del schema["properties"]["__aura_context"]
            tools.append(Tool(name=defn.name, description=defn.description, inputSchema=schema))
    return tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # EXPLICIT SECURITY CHECK: Never trust __aura_context or organization_id from user-supplied arguments!
    if "__aura_context" in arguments or "organization_id" in arguments or "tenant_id" in arguments:
        arguments.pop("__aura_context", None)
        arguments.pop("organization_id", None)
        arguments.pop("tenant_id", None)

    # STRICTLY rely on connection-level context
    try:
        org_id = mcp_org_id.get()
        perms = mcp_permissions.get()
    except LookupError:
        return [
            TextContent(type="text", text="Error: Unauthenticated. Missing organization context.")
        ]

    # Rate limit check
    import time

    from app.security.rate_limit import get_redis_client
    redis = await get_redis_client()
    key = f"rate_limit:mcp_tool:{org_id}"
    now = time.time()
    window = 60
    limit = 100

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()

    if results[2] > limit:
        return [TextContent(type="text", text="Error: RateLimitExceeded: Too many tool calls.")]

    try:
        tool_executor = mcp_registry.get(name)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]

    risk = tool_executor.definition.risk_level
    if risk == RiskLevel.READ and "tools:read" not in perms:
        return [
            TextContent(
                type="text", text="Error: ToolAuthorizationError: Missing tools:read permission"
            )
        ]
    elif risk == RiskLevel.WRITE and "tools:write" not in perms:
        return [
            TextContent(
                type="text", text="Error: ToolAuthorizationError: Missing tools:write permission"
            )
        ]
    elif risk == RiskLevel.EXTERNAL_SIDE_EFFECT and "tools:external" not in perms:
        return [
            TextContent(
                type="text", text="Error: ToolAuthorizationError: Missing tools:external permission"
            )
        ]

    context = ToolContext(
        organization_id=org_id,
        agent_run_id=uuid.uuid4(),
        execution_id=uuid.uuid4().hex,
        dry_run=arguments.pop("_dry_run", False),
        idempotency_key=arguments.pop("_idempotency_key", None),
        approved=arguments.pop("_approved", False),
        request_id=__import__("structlog").contextvars.get_contextvars().get("request_id"),
    )

    from app.policy.engine import PolicyEngine
    from app.policy.schemas import PolicyContext, PolicyDecision

    policy_ctx = PolicyContext(
        organization_id=org_id,
        user_id=org_id,
        tool_name=name,
        risk_level=risk,
        arguments=arguments,
        permissions=perms,
    )

    policy_decision = PolicyEngine.evaluate(policy_ctx)
    if policy_decision.decision == PolicyDecision.DENY:
        return [TextContent(type="text", text=f"Error: Policy Denied: {policy_decision.reason}")]
    if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
        return [TextContent(type="text", text=f"Error: REQUIRE_APPROVAL: {policy_decision.reason}")]

    result = await mcp_registry.execute(name, arguments, context)
    if result.status == "failed":
        return [TextContent(type="text", text=f"Error: {result.message}")]

    return [TextContent(type="text", text=json.dumps(result.result))]
