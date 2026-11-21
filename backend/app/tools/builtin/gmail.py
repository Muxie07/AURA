import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.database.base import get_session_factory
from app.database.models import ApprovalRequest, ApprovalStatus
from app.services.gmail_service import GmailService
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def gmail_send_approval_handler(
    arguments: dict[str, Any], context: ToolContext
) -> dict[str, Any]:
    """
    Dispatches a real interactive governance approval email
    containing cryptographic one-click Approve and Reject buttons.
    """
    cfg = GmailService.get_config(context.organization_id)
    # The approver is configuration, never a model-chosen value: letting the
    # model pick the recipient would make this an arbitrary-email tool.
    recipient = (
        os.environ.get("AURA_APPROVAL_EMAIL")
        or os.environ.get("GMAIL_RECIPIENT_EMAIL")
        or cfg.get("recipient_email")
    )
    if not recipient:
        raise ValueError("No approver email configured (set AURA_APPROVAL_EMAIL).")

    details = arguments.get("details")
    action_summary = arguments.get("action_summary")
    if not details or not action_summary:
        raise ValueError(
            "gmail.send_approval_request needs 'action_summary' and 'details' describing the "
            "real pending action; AURA will not invent them."
        )
    reason = arguments.get("reason") or "Human approval required by policy."

    session_factory = get_session_factory()
    async with session_factory() as db:
        approval = ApprovalRequest(
            agent_run_id=context.agent_run_id or uuid.uuid4(),
            organization_id=context.organization_id,
            tool_name=arguments.get("tool_name", "quotation.create_draft"),
            action_summary=action_summary,
            action_details=details,
            args_hash="gmail_" + uuid.uuid4().hex[:12],
            status=ApprovalStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)

        dispatch_result = await GmailService.dispatch_approval_request(
            approval_id=approval.id,
            tool_name=approval.tool_name,
            action_summary=action_summary,
            action_details=details,
            reason=reason,
            recipient_email=recipient,
            agent_run_id=approval.agent_run_id,
        )

        return {
            "status": "DISPATCHED",
            "approval_id": str(approval.id),
            "recipient": recipient,
            "subject": dispatch_result.get("subject"),
            "approve_url": dispatch_result.get("approve_url"),
            "deny_url": dispatch_result.get("deny_url"),
            "smtp_delivered": dispatch_result.get("smtp_delivered", False),
            "delivery_provider": dispatch_result.get("delivery_provider", "Gmail API"),
            "notice": f"Email dispatched to {recipient}. Recipient can review and authorize the action via secure cryptographic links.",
        }


gmail_send_approval_def = ToolDefinition(
    name="gmail.send_approval_request",
    description="Dispatches a governance sign-off notification email to the configured approver with one-click review and authorization buttons.",
    input_schema={
        "type": "object",
        "properties": {
            "recipient": {"type": "string", "description": "Target approver email address"},
            "action_summary": {
                "type": "string",
                "description": "Brief description of the action requiring approval",
            },
            "reason": {"type": "string", "description": "Why human approval is required"},
            "details": {"type": "object", "description": "Payload arguments and parameters"},
        },
        "required": [],
    },
    # Notifies only the configured approver, so it must not itself wait for approval.
    risk_level=RiskLevel.WRITE,
    idempotent=False,
)

gmail_send_approval_tool = InternalToolExecutor(
    gmail_send_approval_def, gmail_send_approval_handler
)
