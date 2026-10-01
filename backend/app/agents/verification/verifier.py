from typing import Any, Literal

import structlog
from pydantic import BaseModel

from app.agents.core.nodes import BaseNode
from app.agents.core.state import ActionVerification, AgentNodeState, AgentState, FailureCategory
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.services.llm import LLMService
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)

class FailureDiagnosis(BaseModel):
    category: FailureCategory
    reasoning: str
    recommended_action: Literal["RETRY", "REPLAN", "ASK_USER", "FAIL"]

class VerificationNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "VerificationNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if not state.action_history:
            state.status = AgentNodeState.UNDERSTANDING
            return state

        # Check max tool calls
        if len(state.action_history) >= self.settings.max_tool_calls:
            state.add_error(FailureCategory.TIMEOUT, f"Max tool calls ({self.settings.max_tool_calls}) exceeded.")
            state.status = AgentNodeState.FAILED
            return state

        last_history = state.action_history[-1]

        if last_history.error:
            last_history.verification = ActionVerification(
                success=False,
                confidence=1.0,
                issues=[f"Execution failed: {last_history.error.message}"]
            )
            state.status = AgentNodeState.DIAGNOSING
            return state

        result = last_history.result or {}

        is_success = True
        issues = []

        if result.get("success") is False:
            is_success = False
            issues.append(result.get("error", "Unknown error in result"))

        if "found" in result and not result["found"]:
            is_success = False
            issues.append("Requested entity was not found.")

        if "error" in result:
            is_success = False
            issues.append(result["error"])

        last_history.verification = ActionVerification(
            success=is_success,
            confidence=1.0,
            issues=issues
        )

        if is_success:
            state.status = AgentNodeState.UNDERSTANDING
        else:
            state.status = AgentNodeState.DIAGNOSING

        return state


class DiagnoseNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "DiagnoseNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        last_history = state.action_history[-1]
        issues = last_history.verification.issues if last_history.verification else []

        system_prompt = (
            "You are the AURA Diagnostics Agent.\n"
            "An action failed during execution or verification.\n"
            "Diagnose the failure and recommend the next action: RETRY, REPLAN, ASK_USER, or FAIL.\n"
            "If it's a transient error, recommend RETRY.\n"
            "If the plan is flawed, recommend REPLAN.\n"
            "If missing critical user input, recommend ASK_USER.\n"
            "If unrecoverable, recommend FAIL."
        )

        user_prompt = f"Action: {last_history.action.model_dump_json()}\nIssues: {issues}"

        request = GenerationRequest(organization_id=state.organization_id,
            model=self.settings.fast_model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ],
            temperature=0.0
        )

        try:
            _, diagnosis = await self.llm.generate_structured(request, schema=FailureDiagnosis)

            if diagnosis.recommended_action == "RETRY":
                if state.retry_count >= self.settings.max_replan_attempts:
                    state.add_error(FailureCategory.TIMEOUT, "Max retries exceeded.")
                    state.status = AgentNodeState.FAILED
                else:
                    state.retry_count += 1
                    state.status = AgentNodeState.READY_TO_EXECUTE
            elif diagnosis.recommended_action == "REPLAN":
                state.status = AgentNodeState.REPLANNING
            elif diagnosis.recommended_action == "ASK_USER":
                state.add_error(FailureCategory.BUSINESS_RULE, f"Missing info: {diagnosis.reasoning}")
                state.status = AgentNodeState.WAITING
            else:
                state.add_error(diagnosis.category, diagnosis.reasoning)
                state.status = AgentNodeState.FAILED

        except Exception as e:
            logger.error("diagnose_failed", error=str(e))
            state.add_error(FailureCategory.LLM_FAILURE, f"Diagnosis failed: {e}")
            state.status = AgentNodeState.FAILED

        return state


class ReplanNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "ReplanNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if state.replans >= self.settings.max_replan_attempts:
            state.add_error(FailureCategory.TIMEOUT, f"Max replan attempts ({self.settings.max_replan_attempts}) exceeded.")
            state.status = AgentNodeState.FAILED
            return state

        state.replans += 1

        # Strip current unexecuted steps
        if state.plan:
            executed_ids = [h.action.action_id for h in state.action_history]
            state.plan.steps = [s for s in state.plan.steps if s.id in executed_ids]

        # Move back to PLAN
        state.status = AgentNodeState.PLANNING
        return state
