from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentAction, AgentNodeState, AgentState, FailureCategory
from app.ai.routing.router import ModelRouter, TaskProfile
from app.ai.schemas.generation import GenerationRequest, Message
from app.ai.services.llm import LLMService

logger = structlog.get_logger(__name__)

INVOICE_SELECTOR_PAYLOAD = """<!-- INVOICE_SELECTOR_START -->
{
  "companies": [
    {"name": "Acme Technologies", "email": "contact@acme.com", "address": "100 Innovation Way, Austin, TX"},
    {"name": "Global Telecom Ltd", "email": "procurement@globaltelecom.com", "address": "Cyber City, Gurugram, HR"},
    {"name": "Nexa Communications", "email": "billing@nexacomms.in", "address": "Electronic City, Bangalore, KA"},
    {"name": "Apex Enterprise", "email": "finance@apexenterprise.com", "address": "Financial District, Hyderabad, TS"},
    {"name": "Cloud Infotech Partner", "email": "sales@cloudinfotech.com", "address": "Sector 63, Noida, UP"}
  ],
  "products": [
    {"model": "UC-2000-VE-2T", "category": "GSM- VoLTE Gateway", "desc": "2 Port GSM Volte Gateway", "price": 31763},
    {"model": "UC-2000-VE-4T", "category": "GSM- VoLTE Gateway", "desc": "4 Port GSM Volte Gateway", "price": 42350},
    {"model": "UC-2000-VE-8T", "category": "GSM- VoLTE Gateway", "desc": "8 Port GSM Volte Gateway", "price": 74488},
    {"model": "UC-2000-VF-16T", "category": "GSM- VoLTE Gateway", "desc": "16 Port GSM Volte Gateway", "price": 135520},
    {"model": "UC-2000-VG-32T", "category": "GSM- VoLTE Gateway", "desc": "32 Port GSM Volte Gateway", "price": 181500},
    {"model": "DAG1000-2S", "category": "FXS Gateway", "desc": "2 Port ATA", "price": 4235},
    {"model": "DAG1000-4S", "category": "FXS Gateway", "desc": "4 FXS Gateway (G.711A/U, Echo cancel)", "price": 8894},
    {"model": "DAG1000-8S", "category": "FXS Gateway", "desc": "8 FXS Gateway", "price": 15246},
    {"model": "DAG2000-16S", "category": "FXS Gateway", "desc": "16 FXS Gateway", "price": 25410},
    {"model": "DAG2000-24S", "category": "FXS Gateway", "desc": "24 FXS Gateway", "price": 29040},
    {"model": "DAG1000-4S4O", "category": "Hybrid FXS/FXO", "desc": "4 FXS + 4 FXO Gateway", "price": 18755},
    {"model": "DAG1000-8S8O", "category": "Hybrid FXS/FXO", "desc": "8 FXS + 8 FXO Gateway", "price": 35090},
    {"model": "UC120 Series", "category": "IP PBX", "desc": "IPPBX, 2FXO", "price": 15246},
    {"model": "UC200 Series", "category": "IP PBX", "desc": "IPPBX, 2FXS+2FXO", "price": 31763},
    {"model": "SBC300-10", "category": "Session Border Controller", "desc": "10 concurrent calls & 10 transcoding", "price": 44165},
    {"model": "SBC300-20", "category": "Session Border Controller", "desc": "20 concurrent calls & 20 transcoding", "price": 56628},
    {"model": "SBC1000-050", "category": "Session Border Controller", "desc": "50 concurrent calls & 50 transcoding", "price": 222398},
    {"model": "SBC3000 Chassis", "category": "Session Border Controller", "desc": "SBC3000 Chassis + MCU (Dual backup)", "price": 329967}
  ],
  "tiers": [
    {"id": "end_customer", "name": "End-Customer Price"},
    {"id": "retail", "name": "Retail Price"},
    {"id": "msp", "name": "MSP (Distributor Price)"},
    {"id": "mrp", "name": "MRP"}
  ],
  "tax_rate_percent": 18,
  "warranty": "3 Years Standard Replacement Warranty on all products",
  "freight": "Surface transport charges are Free of Cost (FOC)",
  "support": "24*7 Technical Support"
}
<!-- INVOICE_SELECTOR_END -->"""

QUOTATION_SELECTOR_PAYLOAD = """<!-- QUOTATION_SELECTOR_START -->
{
  "companies": [
    {"name": "Acme Technologies", "email": "contact@acme.com", "address": "100 Innovation Way, Austin, TX"},
    {"name": "Global Telecom Ltd", "email": "procurement@globaltelecom.com", "address": "Cyber City, Gurugram, HR"},
    {"name": "Nexa Communications", "email": "billing@nexacomms.in", "address": "Electronic City, Bangalore, KA"},
    {"name": "Apex Enterprise", "email": "finance@apexenterprise.com", "address": "Financial District, Hyderabad, TS"},
    {"name": "Cloud Infotech Partner", "email": "sales@cloudinfotech.com", "address": "Sector 63, Noida, UP"}
  ],
  "products": [
    {"model": "UC-2000-VE-2T", "category": "DINSTAR GSM/VoLTE Gateway", "desc": "2 Port GSM Volte Gateway with SIP Trunk", "price": 31763},
    {"model": "UC-2000-VE-4T", "category": "DINSTAR GSM/VoLTE Gateway", "desc": "4 Port GSM Volte Gateway with SIP Trunk", "price": 42350},
    {"model": "UC-2000-VE-8T", "category": "DINSTAR GSM/VoLTE Gateway", "desc": "8 Port GSM Volte Gateway with SIP Trunk", "price": 74488},
    {"model": "UC-2000-VF-16T", "category": "DINSTAR GSM/VoLTE Gateway", "desc": "16 Port GSM Volte Gateway Enterprise", "price": 135520},
    {"model": "UC-2000-VG-32T", "category": "DINSTAR GSM/VoLTE Gateway", "desc": "32 Port GSM Volte Gateway High Density", "price": 181500},
    {"model": "DAG1000-2S", "category": "DINSTAR FXS/FXO Gateway", "desc": "2 Port ATA Analog VoIP Gateway", "price": 4235},
    {"model": "DAG1000-4S", "category": "DINSTAR FXS/FXO Gateway", "desc": "4 FXS Gateway (G.711A/U, Echo Cancel)", "price": 8894},
    {"model": "DAG1000-8S", "category": "DINSTAR FXS/FXO Gateway", "desc": "8 FXS Gateway with Echo Cancellation", "price": 15246},
    {"model": "DAG2000-16S", "category": "DINSTAR FXS/FXO Gateway", "desc": "16 FXS Analog VoIP Gateway Rackmount", "price": 25410},
    {"model": "DAG2000-24S", "category": "DINSTAR FXS/FXO Gateway", "desc": "24 FXS Analog VoIP Gateway Rackmount", "price": 29040},
    {"model": "DAG1000-4S4O", "category": "DINSTAR Hybrid Gateway", "desc": "4 FXS + 4 FXO Hybrid Gateway", "price": 18755},
    {"model": "DAG1000-8S8O", "category": "DINSTAR Hybrid Gateway", "desc": "8 FXS + 8 FXO Hybrid Gateway", "price": 35090},
    {"model": "UC120 Series", "category": "DINSTAR IP PBX", "desc": "IPPBX, 2FXO, 60 Concurrent Calls", "price": 15246},
    {"model": "UC200 Series", "category": "DINSTAR IP PBX", "desc": "IPPBX, 2FXS+2FXO, High Capacity", "price": 31763},
    {"model": "SBC300-10", "category": "Session Border Controller", "desc": "10 concurrent calls & 10 transcoding", "price": 44165},
    {"model": "SBC300-20", "category": "Session Border Controller", "desc": "20 concurrent calls & 20 transcoding", "price": 56628},
    {"model": "SBC1000-050", "category": "Session Border Controller", "desc": "50 concurrent calls & 50 transcoding", "price": 222398},
    {"model": "SBC3000 Chassis", "category": "Session Border Controller", "desc": "SBC3000 Chassis + MCU (Dual backup)", "price": 329967},
    {"model": "ENT-DB-001", "category": "Enterprise Solutions", "desc": "Enterprise Clustered Server Instance", "price": 125000}
  ],
  "tiers": [
    {"id": "end_customer", "name": "End-Customer Price (Standard)"},
    {"id": "retail", "name": "Retail Price (Reseller / Dealer)"},
    {"id": "msp", "name": "MSP (Distributor Wholesale)"},
    {"id": "mrp", "name": "MRP (Maximum Retail Price)"}
  ],
  "validity": "30 Calendar Days",
  "warranty": "3 Years Standard Replacement Warranty on all products",
  "freight": "Surface transport charges are Free of Cost (FOC)",
  "support": "24*7 Technical Support"
}
<!-- QUOTATION_SELECTOR_END -->"""

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

        elif tool_name == "invoice.generate":
            if isinstance(result, dict) and "invoice_id" in result:
                comp = result.get("billed_to", {}).get("name", "Client")
                lines.append("### Official Tax Invoice Generated")
                lines.append(
                    f"Tax invoice **{result['invoice_id']}** has been generated for **{comp}** "
                    f"according to the Cloud Infotech Distribution Price List (18% GST & 3 Years Warranty).\n"
                )
                lines.append(f"**invoice.generate result:**")
                lines.append(json.dumps(result, indent=2))
            else:
                lines.append(f"**{tool_name} result:**")
                try:
                    lines.append(json.dumps(result, indent=2))
                except Exception:
                    lines.append(str(result))

        elif tool_name == "quotation.create_draft":
            if isinstance(result, dict) and "quotation_id" in result:
                comp = result.get("company_name", result.get("customer", {}).get("name", "Client"))
                model = result.get("model", "Hardware Solution")
                lines.append("### Official Commercial Quotation Generated")
                lines.append(
                    f"Quotation **{result['quotation_id']}** has been prepared for **{comp}** "
                    f"covering **{model}** with a 30-day validity guarantee and 3 Years Warranty.\n"
                )
                lines.append(f"**quotation.create_draft result:**")
                lines.append(json.dumps(result, indent=2))
            else:
                lines.append(f"**{tool_name} result:**")
                try:
                    lines.append(json.dumps(result, indent=2))
                except Exception:
                    lines.append(str(result))

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

            from app.ai.knowledge.adaptive_engine import AdaptiveEngine
            now_ist = AdaptiveEngine.get_current_ist_time()
            now_str = now_ist.strftime("%A, %d %B %Y %I:%M %p IST")

            sys_prompt = (
                "You are AURA (Autonomous Unified Reliability & Operations Assistant), an enterprise-grade AI system.\n"
                f"CURRENT REAL-TIME SYSTEM CLOCK: {now_str} (Asia/Kolkata, Indian Standard Time, UTC+05:30). Year is {now_ist.year}.\n\n"
                "SYSTEM INSTRUCTIONS:\n"
                "1. If the user asks for the current date, day, time, calendar, or Indian Government Gazetted holidays, provide the accurate real-time information based on the CURRENT REAL-TIME SYSTEM CLOCK above.\n"
                "2. When domain documents (RAG context) are provided for enterprise hardware, quotations, invoices, or incidents, use them to provide precise answers.\n"
                "3. If the user asks for programming code, Python scripts, technical explanations, or general business tasks, respond thoroughly with production-grade solutions.\n"
                "4. Maintain a professional, capable, and intelligent tone like a top-tier LLM."
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
                try:
                    async for chunk in self.llm.stream(req):
                        final_text += chunk
                        await redis_client.publish(f"run_stream_{state.run_id}", chunk)
                except Exception as stream_err:
                    logger.warning("direct_stream_failed_fallback_adaptive", error=str(stream_err))
                    adaptive_ans = AdaptiveEngine.evaluate(state.original_request)
                    req_lower = state.original_request.lower()
                    if adaptive_ans:
                        final_text = adaptive_ans
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                    elif any(w in req_lower for w in ["invoice", "create invoice", "generate invoice", "need an invoice", "need invoice", "give invoice", "bill"]):
                        final_text = (
                            "I can help you generate an official Tax Invoice based on the **Cloud Infotech Distribution Price List**.\n\n"
                            "Please select the target company, hardware model, and pricing tier below:\n\n"
                            + INVOICE_SELECTOR_PAYLOAD
                        )
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                    elif any(w in req_lower for w in ["quotation", "create quotation", "generate quotation", "need quotation", "need a quotation", "draft quotation", "give quotation", "quote"]):
                        final_text = (
                            "I can help you create an official commercial Quotation based on our hardware catalog and rate card.\n\n"
                            "Please select the product from our catalog and enter client company details below:\n\n"
                            + QUOTATION_SELECTOR_PAYLOAD
                        )
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                    elif state.retrieved_context and any(kw in req_lower for kw in ["cloud infotech", "price list", "catalog", "policy", "support", "sla", "p1", "incident", "runbook", "latency", "dinstar", "procedure", "hardware"]):
                        top_ctx = state.retrieved_context[0]
                        final_text = (
                            f"Based on the indexed documentation:\n\n"
                            f"**Source: {top_ctx.get('source', 'Knowledge Base')}**\n\n"
                            f"{top_ctx.get('content', '')}"
                        )
                        await redis_client.publish(f"run_stream_{state.run_id}", final_text)
                    else:
                        raise stream_err

                if (
                    final_text.startswith("I'm currently operating in offline fallback mode")
                    or "cannot perform that specific operation while offline" in final_text
                ):
                    adaptive_ans = AdaptiveEngine.evaluate(state.original_request)
                    if adaptive_ans:
                        final_text = adaptive_ans
                    else:
                        final_text = (
                            "I am ready to assist you. You can ask for an official Quotation, Tax Invoice, Indian Government Holidays, Date & Time, Climate information, or Python coding."
                        )
                state.final_response = final_text
                state.status = AgentNodeState.COMPLETED
            except Exception as e:
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
                    if state.action_history:
                        # Tools were executed. Synthesize structured response from real tool data.
                        structured = _generate_structured_response(state)
                        if structured:
                            final_text = structured
                            await redis_client.publish(
                                f"run_stream_{state.run_id}", structured
                            )
                            state.final_response = final_text
                            state.status = AgentNodeState.COMPLETED
                            return state

                    rag_context = ""
                    if state.retrieved_context:
                        rag_context = "\n--- RAG CONTEXT ---\n" + "\n".join(
                            [f"Source: {c['source']}\n{c['content']}" for c in state.retrieved_context]
                        )
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
                        if (
                            final_text.startswith("I'm currently operating in offline fallback mode")
                            or "cannot perform that specific operation while offline" in final_text
                        ):
                            final_text = (
                                "AURA is operating in offline mode and no tool data is "
                                "available to answer this request right now."
                            )
                        state.final_response = final_text
                        state.status = AgentNodeState.COMPLETED
                except Exception as e:
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
            f"Original User Request: {state.original_request}\n\n{rag_context}History:\n{history_context}\n\nWhat are the exact actions to take?"
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
            state.add_error(FailureCategory.LLM_FAILURE, f"Decision failed: {e}")

            state.status = AgentNodeState.FAILED

        return state


