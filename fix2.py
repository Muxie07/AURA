import os
import re

with open("backend/app/api/v1/agent.py", "r") as f:
    content = f.read()

# First fix the duplicate routes (remove everything from the first duplicate trace route onwards)
idx = content.rfind('@router.get("/agent/runs/{run_id}/trace")')
first_idx = content.find('@router.get("/agent/runs/{run_id}/trace")')
if idx != first_idx:
    content = content[:idx]

# Now, ensure all routes use CurrentUserDep and filter by current_user.organization_id
# For get_agent_run
content = re.sub(
    r'(async def get_agent_run\(run_id: uuid\.UUID,\s*db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'run = await db.scalar(sa.select(AgentRun).where(AgentRun.id == run_id))',
    'run = await db.scalar(sa.select(AgentRun).join(Conversation).where(AgentRun.id == run_id, Conversation.organization_id == current_user.organization_id))'
)

# For get_agent_events
content = re.sub(
    r'(async def get_agent_events\(run_id: uuid\.UUID,\s*db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'sa.select(AuditEvent).where(AuditEvent.agent_run_id == run_id).order_by(AuditEvent.created_at)',
    'sa.select(AuditEvent).join(AgentRun).join(Conversation).where(AuditEvent.agent_run_id == run_id, Conversation.organization_id == current_user.organization_id).order_by(AuditEvent.created_at)'
)

# For get_agent_trace
content = re.sub(
    r'(async def get_agent_trace\(run_id: uuid\.UUID,\s*db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'sa.select(AgentTraceEvent).where(AgentTraceEvent.run_id == run_id).order_by(AgentTraceEvent.sequence)',
    'sa.select(AgentTraceEvent).join(AgentRun).join(Conversation).where(AgentTraceEvent.run_id == run_id, Conversation.organization_id == current_user.organization_id).order_by(AgentTraceEvent.sequence)'
)

# For list_approvals
content = re.sub(
    r'(async def list_approvals\(db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'sa.select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())',
    'sa.select(ApprovalRequest).join(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(ApprovalRequest.created_at.desc())'
)

# For approve_request
content = re.sub(
    r'(async def approve_request\(approval_id: uuid\.UUID,\s*db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'approval = await db.scalar(sa.select(ApprovalRequest).where(ApprovalRequest.id == approval_id))',
    'approval = await db.scalar(sa.select(ApprovalRequest).join(AgentRun).join(Conversation).where(ApprovalRequest.id == approval_id, Conversation.organization_id == current_user.organization_id))'
)

# For reject_request
content = re.sub(
    r'(async def reject_request\(approval_id: uuid\.UUID,\s*db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'approval = await db.scalar(sa.select(ApprovalRequest).where(ApprovalRequest.id == approval_id))',
    'approval = await db.scalar(sa.select(ApprovalRequest).join(AgentRun).join(Conversation).where(ApprovalRequest.id == approval_id, Conversation.organization_id == current_user.organization_id))'
)

# For list_agent_runs
content = re.sub(
    r'(async def list_agent_runs\(db:\s*DatabaseDep)(\)\s*->\s*Any:)',
    r'\1, current_user: CurrentUserDep\2',
    content
)
content = content.replace(
    'sa.select(AgentRun).order_by(AgentRun.started_at.desc())',
    'sa.select(AgentRun).join(Conversation).where(Conversation.organization_id == current_user.organization_id).order_by(AgentRun.started_at.desc())'
)

with open("backend/app/api/v1/agent.py", "w") as f:
    f.write(content)
