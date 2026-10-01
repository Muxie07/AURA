with open("backend/app/agents/core/retriever.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("state.status = AgentNodeState.READY_TO_EXECUTE # We'll let graph handle transitions", "state.status = AgentNodeState.UNDERSTANDING")
text = text.replace("state.status = AgentNodeState.READY_TO_EXECUTE", "state.status = AgentNodeState.UNDERSTANDING")

with open("backend/app/agents/core/retriever.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("backend/app/agents/core/builtin_nodes.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
verif_old = """
        if state.errors:
            state.status = AgentNodeState.DIAGNOSING
            return state
        state.status = AgentNodeState.COMPLETED
        return state
"""
verif_new = """
        if state.errors:
            state.status = AgentNodeState.DIAGNOSING
            return state
        state.status = AgentNodeState.UNDERSTANDING
        return state
"""
text = text.replace(verif_old.strip(), verif_new.strip())

with open("backend/app/agents/core/builtin_nodes.py", "w", encoding="utf-8") as f:
    f.write(text)
