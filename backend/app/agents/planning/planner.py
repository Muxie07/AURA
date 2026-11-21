import json
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
        raw_text = (state.original_request or "").strip()
        req_lower = raw_text.lower()

        # Helper to stream response via Redis PubSub immediately
        async def _publish_stream(text: str):
            try:
                import redis.asyncio as aioredis

                from app.config.settings import get_settings

                r_client = aioredis.from_url(get_settings().redis_url, socket_timeout=2.0)
                await r_client.publish(f"run_stream_{state.run_id}", text)
                await r_client.aclose()
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 1. SCOPE FILTER: Politely inform client if query is outside AURA's scope
        # ---------------------------------------------------------------------
        irrelevant_patterns = [
            "python script",
            "write a python",
            "write python",
            "python code",
            "create a python",
            "write a script",
            "bash script",
            "powershell script",
            "write code to",
            "write java",
            "write c++",
            "write javascript",
            "solve leetcode",
            "snake game",
            "tic tac toe",
            "write an essay",
            "write a poem",
            "solve my homework",
            "tell me a joke",
        ]
        is_irrelevant = any(p in req_lower for p in irrelevant_patterns)
        if is_irrelevant and not any(
            aura_kw in req_lower
            for aura_kw in [
                "quotation",
                "invoice",
                "catalog",
                "aura",
                "agent",
                "tool",
                "mcp",
                "utcp",
            ]
        ):
            state.final_response = (
                "This request is outside the scope of AURA.\n\n"
                "AURA is an enterprise AI agent platform specialized in autonomous enterprise operations, commercial quotation drafting, tax invoicing, hardware catalog pricing, RAG enterprise knowledge retrieval, execution monitoring, and governance approvals.\n\n"
                "I can only assist with AURA's enterprise capabilities. Please submit a request related to AURA's commercial operations, catalog pricing, quotation drafting, or platform observability."
            )
            await _publish_stream(state.final_response)
            state.status = AgentNodeState.COMPLETED
            return state

        # ---------------------------------------------------------------------
        # 2. FAST-PATH: Commercial Quotation Intent
        # ---------------------------------------------------------------------
        quotation_triggers = [
            "quotation",
            "quote",
            "commercial quotation",
            "create quotation",
            "generate quote",
            "draft quotation",
            "new quote",
        ]
        if any(t in req_lower for t in quotation_triggers):
            # Check if user wants to retrieve / show / search / query date of an existing quotation
            is_show_quote = any(
                w in req_lower
                for w in [
                    "show",
                    "get",
                    "fetch",
                    "find",
                    "view",
                    "display",
                    "check",
                    "current",
                    "recent",
                    "last",
                    "latest",
                    "where is",
                    "look up",
                    "see",
                    "when",
                    "date",
                    "what date",
                    "which date",
                    "tell me",
                    "details",
                    "status",
                    "history",
                    "search",
                    "time",
                    "created",
                ]
            ) and not any(w in req_lower for w in ["create new", "generate new", "draft new"])
            if is_show_quote:
                from app.tools.builtin.quotations import find_stored_quotation

                stored_q = find_stored_quotation(raw_text)
                if stored_q:
                    comp_name = stored_q.get("company_name", "Client")
                    qid = stored_q.get("quotation_id", "Q-OFFICIAL")
                    created_date = stored_q.get("created_date_formatted") or stored_q.get(
                        "quotation_date", "17.11.2026"
                    )
                    valid_until = stored_q.get("valid_until_formatted") or stored_q.get(
                        "valid_until", "30 Calendar Days"
                    )

                    is_date_query = any(
                        w in req_lower for w in ["date", "when", "time", "created", "day"]
                    )
                    date_header = (
                        (
                            f"### 📅 Official Commercial Quotation Record & Date\n\n"
                            f"- **Client Company:** **{comp_name}**\n"
                            f"- **Quotation Reference:** `{qid}`\n"
                            f"- **Quotation Creation Date:** **{created_date}**\n"
                            f"- **Validity Period:** Valid until **{valid_until}**\n"
                            f"- **Commercial Status:** {stored_q.get('status', 'APPROVED').upper()}\n\n"
                        )
                        if is_date_query
                        else (
                            f"### Official Commercial Quotation on Record\n"
                            f"Here is the official commercial quotation on record for **{comp_name}** (`{qid}`), generated on **{created_date}**:\n\n"
                        )
                    )

                    state.final_response = (
                        date_header + f"**quotation.create_draft result:**\n"
                        f"{json.dumps(stored_q, indent=2)}"
                    )
                    await _publish_stream(state.final_response)
                    state.status = AgentNodeState.COMPLETED
                    return state

            # Check if this is already a finalized execution request with specific details
            has_specific_params = any(
                kw in req_lower
                for kw in ["quantity:", "company_name:", "price_tier:", "discount_percent:"]
            ) or ("for " in req_lower and "units of" in req_lower)
            if not has_specific_params:
                from app.agents.execution.decision import QUOTATION_SELECTOR_PAYLOAD

                state.final_response = (
                    "I can help you create an official commercial Quotation based on our hardware catalog and rate card.\n\n"
                    "Please select the product from our catalog and enter client company details below:\n\n"
                    + QUOTATION_SELECTOR_PAYLOAD
                )
                await _publish_stream(state.final_response)
                state.status = AgentNodeState.COMPLETED
                return state

        # ---------------------------------------------------------------------
        # 3. FAST-PATH: Tax Invoice Intent
        # ---------------------------------------------------------------------
        invoice_triggers = [
            "tax invoice",
            "invoice",
            "generate invoice",
            "create invoice",
            "bill",
            "billing",
        ]
        if any(t in req_lower for t in invoice_triggers):
            # Check if user wants to retrieve / show / search / query date of an existing invoice
            is_show_invoice = any(
                w in req_lower
                for w in [
                    "show",
                    "get",
                    "fetch",
                    "find",
                    "view",
                    "display",
                    "check",
                    "current",
                    "recent",
                    "last",
                    "latest",
                    "where is",
                    "look up",
                    "see",
                    "when",
                    "date",
                    "what date",
                    "which date",
                    "tell me",
                    "details",
                    "status",
                    "history",
                    "search",
                    "time",
                    "created",
                ]
            ) and not any(w in req_lower for w in ["create new", "generate new"])
            if is_show_invoice:
                from app.tools.builtin.invoices import find_stored_invoice

                stored_inv = find_stored_invoice(raw_text)
                if stored_inv:
                    comp_name = stored_inv.get("billed_to", {}).get("name", "Client")
                    inv_id = stored_inv.get("invoice_id", "INV-OFFICIAL")
                    created_date = stored_inv.get("created_date_formatted") or stored_inv.get(
                        "invoice_date", "17.11.2026"
                    )
                    due_date = stored_inv.get("due_date_formatted") or stored_inv.get(
                        "due_date", "30 days"
                    )

                    is_date_query = any(
                        w in req_lower for w in ["date", "when", "time", "created", "day"]
                    )
                    date_header = (
                        (
                            f"### 📅 Official Tax Invoice Record & Creation Date\n\n"
                            f"- **Client / Billed To:** **{comp_name}**\n"
                            f"- **Invoice Number:** `{inv_id}`\n"
                            f"- **Invoice Creation Date:** **{created_date}**\n"
                            f"- **Payment Due Date:** **{due_date}**\n"
                            f"- **Commercial Status:** {stored_inv.get('status', 'APPROVED')} & ISSUED\n"
                            f"- **Warranty Period:** 3 Years Comprehensive DINSTAR Hardware Warranty\n\n"
                        )
                        if is_date_query
                        else (
                            f"### Official Tax Invoice on Record\n"
                            f"Here is the current official Tax Invoice for **{comp_name}** (`{inv_id}`), created on **{created_date}**:\n\n"
                        )
                    )

                    state.final_response = (
                        date_header + f"**invoice.generate result:**\n"
                        f"{json.dumps(stored_inv, indent=2)}"
                    )
                    await _publish_stream(state.final_response)
                    state.status = AgentNodeState.COMPLETED
                    return state

            has_specific_params = any(
                kw in req_lower
                for kw in ["quantity:", "company_name:", "price_tier:", "discount_percent:"]
            ) or ("for " in req_lower and "units of" in req_lower)
            if not has_specific_params:
                from app.agents.execution.decision import INVOICE_SELECTOR_PAYLOAD

                state.final_response = (
                    "I can help you generate an official Tax Invoice based on the **Cloud Infotech Distribution Price List**.\n\n"
                    "Please select the target company, hardware model, and pricing tier below:\n\n"
                    + INVOICE_SELECTOR_PAYLOAD
                )
                await _publish_stream(state.final_response)
                state.status = AgentNodeState.COMPLETED
                return state

        # ---------------------------------------------------------------------
        # 3a. FAST-PATH: Client Commercial Memory & Purchase History Intent
        # ---------------------------------------------------------------------
        client_memory_triggers = [
            "what did",
            "buy",
            "bought",
            "order",
            "ordered",
            "purchase",
            "purchased",
            "search",
            "history",
            "record",
            "records",
            "transaction",
            "transactions",
            "memory",
            "tell me about",
            "client",
            "customer",
        ]
        if any(t in req_lower for t in client_memory_triggers) and not any(
            w in req_lower for w in ["python", "code", "script"]
        ):
            from app.tools.builtin.invoices import find_stored_invoice

            stored_inv = find_stored_invoice(raw_text)
            if stored_inv:
                comp_name = stored_inv.get("billed_to", {}).get("name", "Client")
                inv_id = stored_inv.get("invoice_id", "INV-OFFICIAL")
                created_date = stored_inv.get("created_date_formatted") or stored_inv.get(
                    "invoice_date", "17.11.2026"
                )
                due_date = stored_inv.get("due_date_formatted") or stored_inv.get(
                    "due_date", "30 days"
                )
                items = stored_inv.get("items", [])
                items_summary = ", ".join(
                    [f"{it.get('quantity')} units of {it.get('model')}" for it in items]
                )
                grand_total = stored_inv.get("grand_total", 0.0)

                state.final_response = (
                    f"### 📋 Client Commercial Activity & Memory on Record\n\n"
                    f"According to the enterprise memory and knowledge base for **{comp_name}**:\n\n"
                    f"- **Transaction:** Official Tax Invoice (`{inv_id}`)\n"
                    f"- **Date Generated:** **{created_date}**\n"
                    f"- **Items Ordered:** **{items_summary}**\n"
                    f"- **Total Amount:** **₹{grand_total:,.2f}** (inc. 18% GST)\n"
                    f"- **Payment Due Date:** {due_date}\n"
                    f"- **Status:** {stored_inv.get('status', 'APPROVED')} & ISSUED\n\n"
                    f"Here is the interactive official invoice card:\n\n"
                    f"**invoice.generate result:**\n"
                    f"{json.dumps(stored_inv, indent=2)}"
                )
                await _publish_stream(state.final_response)
                state.status = AgentNodeState.COMPLETED
                return state

        # ---------------------------------------------------------------------
        # 4. FAST-PATH: Common Enterprise Queries (Holidays, Time, Date)
        # ---------------------------------------------------------------------
        if "holiday" in req_lower and any(
            w in req_lower for w in ["gazetted", "indian", "government", "official"]
        ):
            state.final_response = (
                "### Official Indian Government Gazetted Holidays (2026)\n\n"
                "| Date | Day | Holiday | Type |\n"
                "|---|---|---|---|\n"
                "| 26 Jan 2026 | Monday | Republic Day | Gazetted |\n"
                "| 04 Mar 2026 | Wednesday | Holi | Gazetted |\n"
                "| 21 Mar 2026 | Saturday | Id-ul-Fitr | Gazetted |\n"
                "| 03 Apr 2026 | Friday | Good Friday | Gazetted |\n"
                "| 14 Apr 2026 | Tuesday | Dr. B.R. Ambedkar Jayanti | Gazetted |\n"
                "| 01 May 2026 | Friday | Buddha Purnima | Gazetted |\n"
                "| 27 May 2026 | Wednesday | Bakrid / Id-ul-Zuha | Gazetted |\n"
                "| 26 Jun 2026 | Friday | Muharram | Gazetted |\n"
                "| 15 Aug 2026 | Saturday | Independence Day | Gazetted |\n"
                "| 04 Sep 2026 | Friday | Milad-un-Nabi | Gazetted |\n"
                "| 02 Oct 2026 | Friday | Mahatma Gandhi Jayanti | Gazetted |\n"
                "| 20 Oct 2026 | Tuesday | Dussehra (Vijaya Dashami) | Gazetted |\n"
                "| 08 Nov 2026 | Sunday | Diwali (Deepavali) | Gazetted |\n"
                "| 24 Nov 2026 | Tuesday | Guru Nanak Jayanti | Gazetted |\n"
                "| 25 Dec 2026 | Friday | Christmas Day | Gazetted |\n\n"
                "*(All AURA enterprise scheduled operations automatically adhere to the official gazetted calendar.)*"
            )
            await _publish_stream(state.final_response)
            state.status = AgentNodeState.COMPLETED
            return state

        if any(
            w in req_lower
            for w in [
                "what day is today",
                "current time",
                "what is the date",
                "today date",
                "current day",
            ]
        ):
            from datetime import UTC, datetime, timedelta

            now_utc = datetime.now(UTC)
            now_ist = now_utc + timedelta(hours=5, minutes=30)
            state.final_response = (
                f"**Current System Time & Date:**\n\n"
                f"- **IST (India Standard Time):** {now_ist.strftime('%A, %d %B %Y | %I:%M:%S %p')} IST\n"
                f"- **UTC:** {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"- **Platform Status:** All AURA agent schedulers and cron services operational."
            )
            await _publish_stream(state.final_response)
            state.status = AgentNodeState.COMPLETED
            return state

        # ---------------------------------------------------------------------
        # 5. LLM-BASED INTENT UNDERSTANDING (with strict 4s timeout & graceful fallback)
        # ---------------------------------------------------------------------
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
                    cost_sensitivity="LOW",
                )
            ).model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=state.original_request),
            ],
            temperature=0.0,
        )

        try:
            import asyncio

            _, understanding = await asyncio.wait_for(
                self.llm.generate_structured(request, schema=IntentUnderstanding), timeout=4.0
            )

            state.normalized_request = understanding.normalized_request

            if understanding.requires_clarification:
                state.final_response = (
                    understanding.clarification_question or "Could you please clarify your request?"
                )
                await _publish_stream(state.final_response)
                state.status = AgentNodeState.COMPLETED
                return state

            if not understanding.is_safe:
                state.final_response = f"I cannot execute this request. {understanding.reasoning}"
                await _publish_stream(state.final_response)
                state.status = AgentNodeState.COMPLETED
                return state

            state.status = AgentNodeState.PLANNING
        except Exception as e:
            logger.warning("understand_node_llm_fallback", error=str(e), run_id=str(state.run_id))
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

        # Dynamic tools inspection
        registry = kwargs.get("registry")
        extra_tools_block = ""
        if registry and hasattr(registry, "list_definitions"):
            try:
                defs = registry.list_definitions()
                ext_tools = [d for d in defs if d.source in ("utcp", "mcp")]
                if ext_tools:
                    extra_tools_block = "\n" + "\n".join(
                        [f"- {d.name} — {d.description}" for d in ext_tools]
                    )
            except Exception:
                pass

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
            '  Parameters: {"time_range": "24h"} (required), optionally {"endpoint_prefix": "/api/v1"}\n'
            + extra_tools_block
            + "\n\n"
            "RULES:\n"
            "1. For ANY question about API performance, latency, response times, slow endpoints,\n"
            "   errors, request counts, system health — use 'observability.get_api_latency'.\n"
            "2. Use EXACT tool names as the step 'type' field.\n"
            "3. If no tool applies, return an empty steps list with a descriptive goal.\n"
            "4. Keep plans minimal — 1-3 steps only."
        )

        request = GenerationRequest(
            organization_id=state.organization_id,
            model=ModelRouter.route_task(
                TaskProfile(
                    task_type="COMPLEX_REASONING",
                    complexity="HIGH",
                    requires_tools=False,
                    requires_rag=False,
                    requires_structured_output=True,
                    context_length=len(system_prompt)
                    + len(state.normalized_request or state.original_request),
                    latency_requirement="LOW",
                    cost_sensitivity="HIGH",
                )
            ).model,
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=state.normalized_request or state.original_request),
            ],
            temperature=0.0,
        )

        req_str = (state.normalized_request or state.original_request or "").lower()
        if "invoice" in req_str and any(
            k in req_str for k in ["for ", "units", "tier", "generate", "create"]
        ):
            state.plan = AgentPlan(
                goal="Generate official tax invoice from Cloud Infotech price list",
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        type="invoice.generate",
                        description="Generate official tax invoice with 18% GST and 3-yr warranty",
                        dependencies=[],
                        required_tools=["invoice.generate"],
                        risk="LOW",
                        expected_output="Tax invoice generated successfully",
                        verification_criteria="None",
                    )
                ],
            )
            state.status = AgentNodeState.RETRIEVING
            return state

        if "quotation" in req_str and any(
            k in req_str for k in ["for ", "units", "tier", "generate", "create"]
        ):
            state.plan = AgentPlan(
                goal="Generate official commercial quotation from catalog",
                steps=[
                    AgentPlanStep(
                        id="step_1",
                        type="quotation.create_draft",
                        description="Generate official commercial quotation",
                        dependencies=[],
                        required_tools=["quotation.create_draft"],
                        risk="LOW",
                        expected_output="Quotation generated successfully",
                        verification_criteria="None",
                    )
                ],
            )
            state.status = AgentNodeState.RETRIEVING
            return state

        try:
            _result, parsed_plan = await self.llm.generate_structured(
                request, schema=StructuredAgentPlan
            )

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
                    verification_criteria=s.verification_criteria,
                )
                for s in parsed_plan.steps
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
                state.plan = AgentPlan(
                    goal="Respond to user without tools due to planning failure.", steps=[]
                )
                state.status = AgentNodeState.RETRIEVING

        return state
