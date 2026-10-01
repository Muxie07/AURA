from typing import Any

import structlog

from app.agents.core.nodes import BaseNode
from app.agents.core.state import (
    AgentNodeState,
    AgentPlan,
    AgentPlanStep,
    AgentState,
    FailureCategory,
)
from app.agents.planning.schemas import StructuredAgentPlan
from app.ai.routing.router import ModelRouter, TaskProfile
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.services.llm import LLMService

logger = structlog.get_logger(__name__)

class UnderstandNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    @property
    def name(self) -> str:
        return "UnderstandNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        system_prompt = (
            "You are the AURA NLP Agent.\n"
            "Your task is to analyze the user's raw request, fix grammatical/spelling errors, and determine if it is SAFE to execute.\n"
            "1. If the request is a simple query/read, it is safe.\n"
            "2. If the request implies a destructive action (DELETE, DROP, CANCEL, DESTROY) or a write without enough context, it is UNSAFE. Mark 'is_safe': false.\n"
            "3. If the request is ambiguous (e.g. 'do it', 'create one'), it requires clarification. Mark 'requires_clarification': true, and provide a 'clarification_question'.\n"
            "4. For WRITE operations, if the user explicitly provides sufficient context, it is safe.\n"
            "NEVER guess destructive intent. NEVER execute if ambiguous."
        )

        from app.agents.planning.schemas import IntentUnderstanding
        from app.ai.routing.router import ModelRouter, TaskProfile
        from app.ai.schemas.generation import GenerationRequest, Message

        request = GenerationRequest(
            organization_id=state.organization_id,
            model=ModelRouter.route_task(
                TaskProfile(
                    task_type="SIMPLE_CLASSIFICATION",
                    complexity="LOW",
                    requires_tools=False,
                    requires_rag=False,
                    requires_structured_output=True,
                    context_length=len(system_prompt) + len(state.original_request),
                    latency_requirement="HIGH",
                    cost_sensitivity="LOW"
                )
            ).model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=state.original_request)
            ],
            temperature=0.0
        )

        try:
            _, understanding = await self.llm.generate_structured(request, schema=IntentUnderstanding)
            
            state.normalized_request = understanding.normalized_request
            
            if understanding.requires_clarification:
                state.final_response = understanding.clarification_question or "Could you please clarify your request?"
                state.status = AgentNodeState.COMPLETED
                return state
                
            if not understanding.is_safe:
                state.final_response = f"I cannot execute this request. {understanding.reasoning}"
                state.status = AgentNodeState.COMPLETED
                return state

            state.status = AgentNodeState.PLANNING
        except Exception as e:
            logger.error("understand_node_failed", error=str(e), run_id=str(state.run_id))
            # Fallback to basic processing if LLM fails
            state.normalized_request = state.original_request.strip()
            state.status = AgentNodeState.PLANNING
            
        return state

class PlanNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    @property
    def name(self) -> str:
        return "PlanNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if state.plan:
            # We already have a plan (e.g. Replanning phase, which we skip in this basic version)
            state.status = AgentNodeState.RETRIEVING
            return state

        system_prompt = (
            "You are the AURA Planning Agent.\n"
            "Analyze the user's request and create a minimal, precise execution plan.\n\n"
            "REGISTERED TOOLS (use EXACT names as the step 'type'):\n"
            "- customer.search  — search customers by name/email\n"
            "- customer.get     — retrieve customer by ID\n"
            "- product.search   — search product catalog\n"
            "- product.get      — retrieve product by ID\n"
            "- pricing.get      — get pricing for a product\n"
            "- pricing.calculate — calculate price with quantity/discount\n"
            "- quotation.create_draft — create a draft quotation\n"
            "- crm.create_activity   — log a CRM activity\n"
            "- communication.create_email_draft — draft an email\n"
            "- observability.get_api_latency — retrieve real API latency, request count,\n"
            "  error rate, slowest endpoints from the live observability datastore.\n"
            "  Parameters: {\"time_range\": \"24h\"} (required), optionally {\"endpoint_prefix\": \"/api/v1\"}\n\n"
            "RULES:\n"
            "1. For ANY question about API performance, latency, response times, slow endpoints,\n"
            "   errors, request counts, system health — use 'observability.get_api_latency'.\n"
            "2. Use EXACT tool names as the step 'type' field.\n"
            "3. If no tool applies, return an empty steps list with a descriptive goal.\n"
            "4. Keep plans minimal — 1-3 steps only."
        )

        request = GenerationRequest(organization_id=state.organization_id,
            model=ModelRouter.route_task(
                TaskProfile(
                    task_type="COMPLEX_REASONING",
                    complexity="HIGH",
                    requires_tools=False,
                    requires_rag=False,
                    requires_structured_output=True,
                    context_length=len(system_prompt) + len(state.normalized_request or state.original_request),
                    latency_requirement="LOW",
                    cost_sensitivity="HIGH"
                )
            ).model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=state.normalized_request or state.original_request)
            ],
            temperature=0.0
        )

        try:
            _result, parsed_plan = await self.llm.generate_structured(request, schema=StructuredAgentPlan)

            # Map to core domain model
            steps = [
                AgentPlanStep(
                    id=s.id,
                    type=s.type,
                    description=s.description,
                    dependencies=s.dependencies,
                    required_tools=s.required_tools,
                    risk=s.risk,
                    expected_output=s.expected_output,
                    verification_criteria=s.verification_criteria
                ) for s in parsed_plan.steps
            ]
            state.plan = AgentPlan(goal=parsed_plan.goal, steps=steps)

            state.status = AgentNodeState.RETRIEVING

        except Exception as e:
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


        return state
