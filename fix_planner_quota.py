with open("backend/app/agents/planning/planner.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
replacement = """        except Exception as e:
            from app.ai.errors.exceptions import LLMQuotaExceededError
            logger.error("planner_failed", error=str(e), run_id=str(state.run_id))
            
            if isinstance(e, LLMQuotaExceededError):
                state.add_error(FailureCategory.LLM_FAILURE, "AURA's AI provider has temporarily reached its usage limit. Please try again after the quota resets.")
            else:
                state.add_error(FailureCategory.LLM_FAILURE, f"Planning failed: {e}")
                
            state.status = AgentNodeState.FAILED"""

text = re.sub(r'        except Exception as e:.*?state\.status = AgentNodeState\.FAILED', replacement, text, flags=re.DOTALL)

with open("backend/app/agents/planning/planner.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("backend/app/agents/execution/decision.py", "r", encoding="utf-8") as f:
    dtext = f.read()

d_replacement = """        except Exception as e:
            from app.ai.errors.exceptions import LLMQuotaExceededError
            logger.error("decision_failed", error=str(e), run_id=str(state.run_id))
            
            if isinstance(e, LLMQuotaExceededError):
                state.add_error(FailureCategory.LLM_FAILURE, "AURA's AI provider has temporarily reached its usage limit. Please try again after the quota resets.")
            else:
                state.add_error(FailureCategory.LLM_FAILURE, f"Decision failed: {e}")
                
            state.status = AgentNodeState.FAILED"""

dtext = re.sub(r'        except Exception as e:.*?state\.status = AgentNodeState\.FAILED', d_replacement, dtext, flags=re.DOTALL)

with open("backend/app/agents/execution/decision.py", "w", encoding="utf-8") as f:
    f.write(dtext)
