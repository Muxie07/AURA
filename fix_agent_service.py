with open("backend/app/agents/services/agent_service.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
replacement = """            elif run.status == AgentRunStatus.FAILED:
                msg_content = run.error_message if run.error_message and run.error_message.startswith("AURA") else f"AURA encountered an error: {run.error_message}"
                assistant_msg = Message(
                    conversation_id=run.conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=msg_content,
                    agent_run_id=run.id
                )"""

text = re.sub(r'            elif run\.status == AgentRunStatus\.FAILED:\n\s*assistant_msg = Message\(\n\s*conversation_id=run\.conversation_id,\n\s*role=MessageRole\.ASSISTANT,\n\s*content=f"AURA encountered an error: \{run\.error_message\}",\n\s*agent_run_id=run\.id\n\s*\)', replacement, text, flags=re.DOTALL)

with open("backend/app/agents/services/agent_service.py", "w", encoding="utf-8") as f:
    f.write(text)
