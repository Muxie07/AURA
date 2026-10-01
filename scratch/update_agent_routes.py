import re

with open('app/api/v1/agent.py', 'r') as f:
    text = f.read()

text = text.replace(
    'agent_service = AgentWorkflowService(db, llm, rag)\n    try:',
    'agent_service = AgentWorkflowService(db, llm, rag)\n    await agent_service.initialize()\n    try:'
)

with open('app/api/v1/agent.py', 'w') as f:
    f.write(text)
