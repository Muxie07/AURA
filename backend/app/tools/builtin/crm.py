import uuid
from typing import Any

from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def crm_create_activity_handler(
    arguments: dict[str, Any], context: ToolContext
) -> dict[str, Any]:
    return {
        "activity_id": f"ACT-{uuid.uuid4().hex[:8]}",
        "status": "logged",
        "customer_id": arguments.get("customer_id"),
    }


crm_create_activity_def = ToolDefinition(
    name="crm.create_activity",
    description="Log an activity in the CRM.",
    input_schema={
        "type": "object",
        "properties": {"customer_id": {"type": "string"}, "note": {"type": "string"}},
        "required": ["customer_id", "note"],
    },
    risk_level=RiskLevel.WRITE,
)

crm_create_activity_tool = InternalToolExecutor(
    crm_create_activity_def, crm_create_activity_handler
)
