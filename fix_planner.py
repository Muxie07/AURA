with open("backend/app/agents/planning/planner.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# We want to replace the try/except block.
# Currently it is:
#         except Exception as e:
#             from app.ai.errors.exceptions import LLMQuotaExceededError
#             logger.error("planner_failed", error=str(e), run_id=str(state.run_id))
#             
#             if isinstance(e, LLMQuotaExceededError):
#                 state.add_error(FailureCategory.LLM_FAILURE, "AURA's AI provider has temporarily reached its usage limit. Please try again after the quota resets.")
#                 state.status = AgentNodeState.FAILED
#             else:
#                 # Safe recovery path: continue without tools if structured planning fails
#                 logger.warning("planner_safe_recovery", error=str(e), run_id=str(state.run_id))
#                 state.plan = AgentPlan(goal="Respond to user without tools due to planning failure.", steps=[])
#                 state.status = AgentNodeState.RETRIEVING

new_except = """        except Exception as e:
            logger.error("planner_failed", error=str(e), run_id=str(state.run_id))
            from app.ai.errors.exceptions import LLMQuotaExceededError
            
            # Safe recovery path: continue without tools if structured planning fails
            # We treat quota exhaustion as a planning failure that can be recovered from
            # if we just want to chat, or fail if we prefer. But actually, if LLMService
            # failed over and still raised, we just recover safely or fail.
            if isinstance(e, LLMQuotaExceededError):
                # We do not return the hardcoded string. We log it and fail.
                state.add_error(FailureCategory.LLM_FAILURE, f"AI Planning failed: {e}")
                state.status = AgentNodeState.FAILED
            else:
                logger.warning("planner_safe_recovery", error=str(e), run_id=str(state.run_id))
                state.plan = AgentPlan(goal="Respond to user without tools due to planning failure.", steps=[])
                state.status = AgentNodeState.RETRIEVING
"""

# Let's just do a manual string replace to be safe.
old_except = """        except Exception as e:
            from app.ai.errors.exceptions import LLMQuotaExceededError
            logger.error("planner_failed", error=str(e), run_id=str(state.run_id))
            
            if isinstance(e, LLMQuotaExceededError):
                state.add_error(FailureCategory.LLM_FAILURE, "AURA's AI provider has temporarily reached its usage limit. Please try again after the quota resets.")
                state.status = AgentNodeState.FAILED
            else:
                # Safe recovery path: continue without tools if structured planning fails
                logger.warning("planner_safe_recovery", error=str(e), run_id=str(state.run_id))
                state.plan = AgentPlan(goal="Respond to user without tools due to planning failure.", steps=[])
                state.status = AgentNodeState.RETRIEVING"""

if old_except in text:
    text = text.replace(old_except, new_except)
    with open("backend/app/agents/planning/planner.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Fixed planner.py")
else:
    print("Could not find exact match in planner.py")
