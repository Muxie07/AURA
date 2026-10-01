import uuid
from typing import Any

from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def communication_create_email_draft_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    return {
        "draft_id": f"EML-{uuid.uuid4().hex[:8]}",
        "recipient": arguments.get("recipient"),
        "subject": arguments.get("subject"),
        "body": arguments.get("body"),
        "status": "draft_created"
    }

communication_create_email_draft_def = ToolDefinition(
    name="communication.create_email_draft",
    description="Create an email draft.",
    input_schema={
        "type": "object",
        "properties": {
            "recipient": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"}
        },
        "required": ["recipient", "subject", "body"]
    },
    risk_level=RiskLevel.WRITE
)

communication_create_email_draft_tool = InternalToolExecutor(communication_create_email_draft_def, communication_create_email_draft_handler)
