with open("backend/app/agents/core/retriever.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

old_except = """
        except Exception as e:
            logger.error("retrieval_node_failed", error=str(e), run_id=str(state.run_id))
            # Retrieval failure is non-fatal usually, we just proceed

        return state
"""

new_except = """
        except Exception as e:
            logger.error("retrieval_node_failed", error=str(e), run_id=str(state.run_id))
            # Retrieval failure is non-fatal usually, we just proceed
            state.status = AgentNodeState.READY_TO_EXECUTE

        return state
"""

text = text.replace(old_except.strip(), new_except.strip())

with open("backend/app/agents/core/retriever.py", "w", encoding="utf-8") as f:
    f.write(text)
