with open("backend/app/agents/services/agent_service.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "graph.add_transition(AgentNodeState.RETRIEVING, lambda s: AgentNodeState.READY_TO_EXECUTE)",
    "graph.add_transition(AgentNodeState.RETRIEVING, lambda s: AgentNodeState.UNDERSTANDING)"
)
text = text.replace(
    "graph.add_transition(AgentNodeState.VERIFYING, lambda s: AgentNodeState.COMPLETED)",
    "graph.add_transition(AgentNodeState.VERIFYING, lambda s: AgentNodeState.UNDERSTANDING)"
)

with open("backend/app/agents/services/agent_service.py", "w", encoding="utf-8") as f:
    f.write(text)
