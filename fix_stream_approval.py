with open('backend/app/api/v1/runs.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    "if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):",
    "if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.AWAITING_APPROVAL):"
)

with open('backend/app/api/v1/runs.py', 'w', encoding='utf-8') as f:
    f.write(text)
