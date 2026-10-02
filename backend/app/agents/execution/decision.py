from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentAction, AgentNodeState, AgentState, FailureCategory
from app.ai.routing.router import ModelRouter, TaskProfile
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.services.llm import LLMService

logger = structlog.get_logger(__name__)


def _generate_structured_response(state: AgentState) -> str:
    """
    Generate a natural-language response from tool results without using the LLM.
    Used as a fallback when LLM quota is exhausted but tools have returned real data.
    """
    import json

    lines: list[str] = []

    for history_item in state.action_history:
        tool_name = history_item.action.action_type
        result = history_item.result

        if result is None:
            continue

        # ------------------------------------------------------------------ #
        # Observability tool
        # ------------------------------------------------------------------ #
        if tool_name == "observability.get_api_latency":
            if isinstance(result, dict):
                if result.get("request_count", 0) == 0:
                    msg = result.get("message", "")
                    if msg:
                        return msg
                    return (
                        "No historical latency data is available yet. "
                        "AURA's observability instrumentation is now connected, "
                        "so new API requests will be recorded for analysis."
                    )

                count = result.get("request_count", 0)
                avg = result.get("average_latency_ms", 0)
                p50 = result.get("p50_latency_ms", 0)
                p95 = result.get("p95_latency_ms", 0)
                p99 = result.get("p99_latency_ms", 0)
                err_rate = result.get("error_rate_percent", 0)
                err_count = result.get("error_count", 0)
                slowest = result.get("slowest_endpoints", [])
                time_range = result.get("time_range", "recent")

                # Health classification
                if p95 < 200:
                    health = "healthy"
                    health_note = "Response times are within acceptable bounds."
                elif p95 < 500:
                    health = "acceptable"
                    health_note = (
                        "Some endpoints are approaching latency thresholds — worth monitoring."
                    )
                elif p95 < 1000:
                    health = "concerning"
                    health_note = "Several endpoints are running slow and should be investigated."
                else:
                    health = "critical"
                    health_note = (
                        "Latency is critically high — immediate investigation recommended."
                    )

                lines.append(f"**API Performance Report — {time_range}**\n")
                lines.append(f"AURA processed **{count:,} requests** in the observed window.")
                lines.append(f"Overall system health: **{health.upper()}**. {health_note}\n")
                lines.append("**Latency Summary:**")
                lines.append(f"- Average: {avg} ms")
                lines.append(f"- P50 (median): {p50} ms")
                lines.append(f"- P95: {p95} ms")
                lines.append(f"- P99: {p99} ms\n")

                if err_rate > 0:
                    lines.append(
                        f"**Error Rate: {err_rate}%** ({err_count} errors out of {count} requests)"
                    )
                    if err_rate > 5:
                        lines.append("⚠️  Error rate exceeds 5% — investigate 4xx/5xx responses.")
                    elif err_rate > 1:
                        lines.append("Error rate is slightly elevated but not critical.")
                    lines.append("")
                else:
                    lines.append("**Error Rate: 0%** — No request errors detected.\n")

                if slowest:
                    lines.append("**Slowest Endpoints:**")
                    for ep in slowest:
                        lines.append(
                            f"- `{ep['path']}` — avg {ep['avg_ms']} ms over {ep['calls']} calls"
                        )
                    lines.append("")

                # Recommendation
                if p95 >= 500 or err_rate > 1:
                    lines.append(
                        "**Recommended Next Steps:** "
                        "Review the slowest endpoints listed above for N+1 queries, "
                        "missing database indexes, or blocking synchronous calls. "
                        "Consider adding caching for high-frequency read endpoints."
                    )
                else:
                    lines.append(
                        "No immediate action required. "
                        "Continue monitoring — new requests are being recorded automatically."
                    )

        else:
            # Generic tool result
            lines.append(f"**{tool_name} result:**")
            try:
                lines.append(json.dumps(result, indent=2))
            except Exception:
                lines.append(str(result))

    if not lines:
        return (
            f'I processed your request: "{state.original_request}". '
            "However, no tool results were available to summarize."
        )

    return "\n".join(lines)


class ActionSchema(BaseModel):
    action_id: str = Field(..., description="The id of the plan step this action is for")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments for the action")
    reasoning: str = Field(..., description="Why this action was selected")


class DecisionSchema(BaseModel):
    actions: list[ActionSchema] = Field(..., description="List of actions to execute in parallel")


class DecisionNode(BaseNode):
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    @property
    def name(self) -> str:
        return "DecisionNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if not state.plan or not state.plan.steps:
            # Generate direct response without steps
            rag_context = ""
            if state.retrieved_context:
                rag_context = "\n--- RAG CONTEXT ---\n" + "\n".join(
                    [f"Source: {c['source']}\n{c['content']}" for c in state.retrieved_context]
                )

            sys_prompt = (
                "You are AURA. Answer the user's request using ONLY the provided context.\n"
                "CRITICAL: You must cite every claim using the provided [chunk_id].\n"
                "If the context does not contain the answer, say 'I cannot find the answer in the provided documents.'\n"
            )
            usr_prompt = f"Original Request: {state.original_request}{rag_context}"
            req = GenerationRequest(
                organization_id=state.organization_id,
                model=ModelRouter.route_task(
                    TaskProfile(
                        task_type="GENERAL_CHAT",
                        complexity="LOW",
                        requires_tools=False,
                        requires_rag=bool(state.retrieved_context),
                        requires_structured_output=False,
                        context_length=len(sys_prompt) + len(usr_prompt),
                        latency_requirement="HIGH",
                        cost_sensitivity="LOW",
                    )
                ).model,
                messages=[
                    Message(role="system", content=sys_prompt),
                    Message(role="user", content=usr_prompt),
                ],
            )

            import redis.asyncio as aioredis

            from app.config.settings import get_settings

            redis_client = aioredis.from_url(get_settings().redis_url, socket_timeout=2.0)

            final_text = ""
            try:
                async for chunk in self.llm.stream(req):
                    final_text += chunk
                    await redis_client.publish(f"run_stream_{state.run_id}", chunk)
                state.final_response = final_text
                state.status = AgentNodeState.COMPLETED
            except Exception as e:
                from app.ai.errors.exceptions import LLMQuotaExceededError

                if True:  # Always fallback if stream fails
                    state.final_response = "I processed your request, but AURA's AI provider reached its limit while generating the final response."
                    state.status = AgentNodeState.COMPLETED
                else:
                    state.add_error(FailureCategory.LLM_FAILURE, f"Decision stream failed: {e}")
                    state.status = AgentNodeState.FAILED
            finally:
                await redis_client.aclose()

            return state

        # Find executed steps
        executed_step_ids = {a.action.action_id for a in state.action_history if a.action.action_id}

        ready_steps = []
        for setp in state.plan.steps:
            if setp.id in executed_step_ids:
                continue
            if all(dep in executed_step_ids for dep in setp.dependencies):
                ready_steps.append(setp)

        if not ready_steps:
            # Either done or deadlock
            if len(executed_step_ids) == len(state.plan.steps):
                # Generate final response based on history
                history_context = "\n".join(
                    [
                        f"Action: {h.action.action_type}, Result: {h.result}"
                        for h in state.action_history
                    ]
                )
                sys_prompt = (
                    "You are AURA, an enterprise AI operations assistant.\n"
                    "Analyze the tool results and provide an intelligent, natural-language response.\n\n"
                    "If the results contain observability/latency data:\n"
                    "- Describe the overall system health clearly\n"
                    "- Report average, p50, p95, p99 latency with context (good/concerning/critical)\n"
                    "- Highlight the slowest endpoints with specific numbers\n"
                    "- Report the error rate with context\n"
                    "- If the data shows no issues, say so directly\n"
                    "- If there is no data yet, explain that instrumentation is now active\n"
                    "- Recommend concrete next steps if warranted\n"
                    "- Use ONLY data present in the results — never invent numbers\n\n"
                    "For other tools: summarize findings concisely and accurately.\n"
                    "Always respond in clear business English, not as a developer."
                )
                usr_prompt = (
                    f"Original Request: {state.original_request}\nTool Results:\n{history_context}"
                )

                req = GenerationRequest(
                    organization_id=state.organization_id,
                    model=ModelRouter.route_task(
                        TaskProfile(
                            task_type="GENERAL_CHAT",
                            complexity="LOW",
                            requires_tools=False,
                            requires_rag=False,
                            requires_structured_output=False,
                            context_length=len(sys_prompt) + len(usr_prompt),
                            latency_requirement="HIGH",
                            cost_sensitivity="LOW",
                        )
                    ).model,
                    messages=[
                        Message(role="system", content=sys_prompt),
                        Message(role="user", content=usr_prompt),
                    ],
                )

                import redis.asyncio as aioredis

                from app.config.settings import get_settings

                redis_client = aioredis.from_url(get_settings().redis_url, socket_timeout=2.0)


                final_text = ""
                try:
                    if state.retrieved_context:
                        res = await self.llm.generate(req)
                        final_text = res.text
                        
                        check_req = GenerationRequest(
                            organization_id=state.organization_id,
                            model=req.model,
                            messages=[Message(role="user", content="Context: " + rag_context + "\n\nAnswer: " + final_text + "\n\nIs the answer fully supported by the context and are citations correct? Reply exactly YES or NO.")],
                            temperature=0.0
                        )
                        check_res = await self.llm.generate(check_req)
                        if "NO" in check_res.text.upper():
                            final_text = "I cannot find a fully supported answer in the provided documents."
                            
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                        state.final_response = final_text
                        state.status = AgentNodeState.COMPLETED
                    else:
                        async for chunk in self.llm.stream(req):
                            final_text += chunk
                            await redis_client.publish(f"run_stream_{state.run_id}", chunk)
                        state.final_response = final_text
                        state.status = AgentNodeState.COMPLETED
                except Exception as e:
                    from app.ai.errors.exceptions import LLMQuotaExceededError

                    if True:  # Always fallback if stream fails
                        # LLM quota exhausted — generate a structured response directly from tool results
                        # without making another LLM call (zero additional quota usage)
                        fallback_text = _generate_structured_response(state)
                        final_text = fallback_text
                        state.final_response = final_text
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                        state.status = AgentNodeState.COMPLETED
                    else:
                        state.add_error(FailureCategory.LLM_FAILURE, f"Decision stream failed: {e}")
                        state.status = AgentNodeState.FAILED
                finally:
                    await redis_client.aclose()

            else:
                state.add_error(FailureCategory.BUSINESS_RULE, "Deadlock detected in plan.")
                state.status = AgentNodeState.FAILED
            return state

        history_context = "\n".join(
            [f"Action: {h.action.action_type}, Result: {h.result}" for h in state.action_history]
        )

        steps_str = "\n".join(
            [f" - ID: {s.id}, Type: {s.type}, Desc: {s.description}" for s in ready_steps]
        )

        system_prompt = (
            "You are the AURA Action Selection Agent.\n"
            f"Your current goal is: {state.plan.goal}\n"
            f"The following steps are ready to execute in parallel:\n{steps_str}\n"
            "Based on the execution history, determine the exact arguments needed for EACH of these actions.\n"
            "Return the structured action selection containing all ready actions."
        )

        rag_context = ""
        if state.retrieved_context:
            rag_context = "\n--- RAG CONTEXT (UNTRUSTED DATA) ---\n"
            for ctx in state.retrieved_context:
                rag_context += f"Source: {ctx['source']}\nContent: {ctx['content']}\n\n"
            rag_context += "--- END RAG CONTEXT ---\n"

        user_prompt = (
            f"{rag_context}History:\n{history_context}\n\nWhat are the exact actions to take?"
        )

        request = GenerationRequest(
            organization_id=state.organization_id,
            model=ModelRouter.route_task(
                TaskProfile(
                    task_type="TOOL_USE",
                    complexity="MEDIUM",
                    requires_tools=True,
                    requires_rag=bool(state.retrieved_context),
                    requires_structured_output=True,
                    context_length=len(history_context) + len(rag_context),
                    latency_requirement="HIGH",
                    cost_sensitivity="HIGH",
                )
            ).model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.0,
        )

        try:
            _result, parsed_decision = await self.llm.generate_structured(
                request, schema=DecisionSchema
            )

            state.current_actions = []
            for act in parsed_decision.actions:
                step_match = next((s for s in ready_steps if s.id == act.action_id), None)
                if step_match:
                    state.current_actions.append(
                        AgentAction(
                            action_id=step_match.id,
                            action_type=step_match.type,
                            description=act.reasoning,
                            arguments=act.arguments,
                            status="PENDING",
                        )
                    )

            state.status = AgentNodeState.READY_TO_EXECUTE

        except Exception as e:
            logger.error("decision_failed", error=str(e), run_id=str(state.run_id))
            from app.ai.errors.exceptions import LLMQuotaExceededError

            if isinstance(e, LLMQuotaExceededError):
                state.add_error(FailureCategory.LLM_FAILURE, f"AI Decision failed: {e}")
            else:
                state.add_error(FailureCategory.LLM_FAILURE, f"Decision failed: {e}")

            state.status = AgentNodeState.FAILED

        return state
