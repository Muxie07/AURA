import asyncio
import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.providers.base import LLMProvider
from app.ai.schemas.generation import GenerationRequest, GenerationResult
from app.ai.schemas.usage import Usage

T = TypeVar("T", bound=BaseModel)


class HeuristicLLMProvider(LLMProvider):
    """
    Offline fallback provider that uses heuristic rule-based logic to
    return valid structured outputs for standard business queries
    when the primary LLM is unavailable due to quota/rate limits.
    """

    @property
    def name(self) -> str:
        return "heuristic"

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        raw_user_msg = request.messages[-1].content if request.messages else ""
        user_msg = raw_user_msg.lower()

        original_req = user_msg
        import re

        match = re.search(
            r"original request:\s*(.*?)(?:\ntool results:|\n--- rag context ---|$)",
            user_msg,
            re.DOTALL,
        )
        if match:
            original_req = match.group(1).strip()

        prompt = original_req

        full_text = "\n".join([m.content or "" for m in request.messages])

        rag_match = re.search(
            r"(?:---\s*rag context.*?---\s*\n|===\s*retrieved context\s*===\s*\n)(.*?)(?:---\s*end rag context\s*---|===\s*end context\s*===|$)",
            full_text,
            re.IGNORECASE | re.DOTALL,
        )

        from app.ai.knowledge.adaptive_engine import AdaptiveEngine
        adaptive_match = AdaptiveEngine.evaluate(prompt)

        # 1. First check if prompt matches adaptive general intelligence (time, holidays, climate, coding, etc.)
        if adaptive_match:
            text = adaptive_match
        # 2. If tool results are provided, acknowledge them instead of repeating offline intro
        elif "tool results:" in user_msg:
            if "observability.get_api_latency" in user_msg:
                text = (
                    "I have retrieved the API latency metrics from the observability system. "
                    "Endpoints were analyzed and metrics are available in the performance report."
                )
            elif "quotation.create_draft" in user_msg:
                text = "The draft quotation has been generated successfully."
            elif "customer" in user_msg:
                text = "Customer details were retrieved successfully."
            else:
                text = "Tool execution completed successfully."
        # 3. If RAG context is provided with indexed chunks, only synthesize if prompt is asking for enterprise documentation
        elif rag_match and rag_match.group(1).strip() and any(k in prompt for k in ["cloud infotech", "price list", "catalog", "hardware", "dinstar", "rate", "cost", "warranty", "sla", "incident", "p1"]):
            raw_rag = rag_match.group(1).strip()
            doc_matches = re.findall(
                r"<source>(.*?)</source>.*?<content>\s*(.*?)\s*</content>",
                raw_rag,
                re.DOTALL,
            )
            if doc_matches:
                primary_doc = doc_matches[0]
                text = f"Based on the indexed documentation:\n\n**Source: {primary_doc[0]}**\n\n{primary_doc[1][:2500]}"
            else:
                text = f"Based on the indexed documentation:\n\n{raw_rag[:2500]}"
        # 4. Targeted offline responses based on user's actual intent
        elif "invoice" in prompt or "bill" in prompt:
            from app.agents.execution.decision import INVOICE_SELECTOR_PAYLOAD

            text = (
                "I can help you generate an official Tax Invoice based on the **Cloud Infotech Distribution Price List**.\n\n"
                "Please select your client company, hardware model, and pricing tier below:\n\n"
                + INVOICE_SELECTOR_PAYLOAD
            )
        elif "quotation" in prompt or "quote" in prompt:
            from app.agents.execution.decision import QUOTATION_SELECTOR_PAYLOAD

            text = (
                "I can help you create an official commercial Quotation based on our hardware catalog and rate card.\n\n"
                "Please select the product from our catalog and enter client company details below:\n\n"
                + QUOTATION_SELECTOR_PAYLOAD
            )
        elif "p1" in prompt or "incident" in prompt:
            text = "I cannot find the P1 incident procedure in the provided knowledge base while operating in offline mode."
        elif "latency" in prompt or "observability" in prompt:
            text = "I'm currently operating in offline fallback mode. I can help you investigate API latency."
        elif "customer" in prompt:
            text = "I'm currently operating in offline fallback mode. I can help you search for customer information."
        elif "product" in prompt:
            text = "I'm currently operating in offline fallback mode. I can help you search for products."
        elif "pricing" in prompt:
            text = "I'm currently operating in offline fallback mode. I can help you calculate pricing."
        else:
            text = (
                "I am ready to assist you. You can ask for an official Quotation, Tax Invoice, Indian Government Holidays, Date & Time, Climate information, or Python coding."
            )

        return GenerationResult(
            text=text,
            model=request.model,
            provider=self.name,
            usage=Usage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            finish_reason="stop",
            raw_response={"heuristic": True},
        )

    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:

        prompt = ""
        for msg in request.messages:
            if msg.content:
                prompt += msg.content.lower() + " "

        data: dict[str, Any] = {}

        user_prompt = ""
        for msg in request.messages:
            if msg.role == "user" and msg.content:
                user_prompt += msg.content.lower() + " "

        if schema.__name__ == "StructuredAgentPlan":
            if "invoice" in user_prompt or "bill" in user_prompt:
                if any(k in user_prompt for k in ["acme", "global", "nexa", "apex", "nova", "uc-", "dag", "sbc", "for ", "generate invoice for", "create invoice for"]):
                    data = {
                        "goal": "Generate official tax invoice from Cloud Infotech price list",
                        "steps": [
                            {
                                "id": "step_1",
                                "type": "invoice.generate",
                                "description": "Generate official tax invoice",
                                "dependencies": [],
                                "required_tools": ["invoice.generate"],
                                "risk": "LOW",
                                "expected_output": "Tax invoice generated successfully",
                                "verification_criteria": "None",
                                "status": "pending",
                            }
                        ],
                    }
                else:
                    data = {"goal": "Prompt user with invoice configuration options", "steps": []}
            elif "quotation" in user_prompt or "quote" in user_prompt:
                if any(k in user_prompt for k in ["acme", "global", "nexa", "apex", "nova", "uc-", "dag", "sbc", "for ", "generate quotation for", "create quotation for", "units", "tier", "draft quotation for"]):
                    data = {
                        "goal": "Generate official commercial quotation from catalog",
                        "steps": [
                            {
                                "id": "step_1",
                                "type": "quotation.create_draft",
                                "description": "Generate official commercial quotation",
                                "dependencies": [],
                                "required_tools": ["quotation.create_draft"],
                                "risk": "LOW",
                                "expected_output": "Quotation generated successfully",
                                "verification_criteria": "None",
                                "status": "pending",
                            }
                        ],
                    }
                else:
                    data = {"goal": "Prompt user with quotation configuration options", "steps": []}
            elif "latency" in user_prompt or "observability" in user_prompt:
                data = {
                    "goal": "Investigate API latency",
                    "steps": [
                        {
                            "id": "step_1",
                            "type": "observability.get_api_latency",
                            "description": "Retrieve recent API latency",
                            "dependencies": [],
                            "required_tools": ["observability.get_api_latency"],
                            "risk": "LOW",
                            "expected_output": "Metrics data",
                            "verification_criteria": "None",
                            "status": "pending",
                        }
                    ],
                }
            elif "product" in user_prompt:
                data = {
                    "goal": "Search products",
                    "steps": [
                        {
                            "id": "step_1",
                            "type": "product.search",
                            "description": "Search product catalog",
                            "dependencies": [],
                            "required_tools": ["product.search"],
                            "risk": "LOW",
                            "expected_output": "Product list",
                            "verification_criteria": "None",
                            "status": "pending",
                        }
                    ],
                }
            elif "pricing" in user_prompt:
                data = {
                    "goal": "Calculate pricing",
                    "steps": [
                        {
                            "id": "step_1",
                            "type": "pricing.calculate",
                            "description": "Calculate product pricing",
                            "dependencies": [],
                            "required_tools": ["pricing.calculate"],
                            "risk": "LOW",
                            "expected_output": "Price calculated",
                            "verification_criteria": "None",
                            "status": "pending",
                        }
                    ],
                }
            elif any(k in user_prompt for k in ["policy", "support policy", "sla", "p1", "incident", "runbook", "procedure"]):
                data = {"goal": "Retrieve and summarize documentation", "steps": []}
            elif "customer" in user_prompt:
                data = {
                    "goal": "Search customers",
                    "steps": [
                        {
                            "id": "step_1",
                            "type": "customer.search",
                            "description": "Search for customer",
                            "dependencies": [],
                            "required_tools": ["customer.search"],
                            "risk": "LOW",
                            "expected_output": "Customer details",
                            "verification_criteria": "None",
                            "status": "pending",
                        }
                    ],
                }
            else:
                data = {"goal": "Respond to user request", "steps": []}

        elif schema.__name__ == "DecisionSchema":
            import re

            sys_prompt = ""
            user_prompt_dec = ""
            for msg in request.messages:
                if msg.role == "system" and msg.content:
                    sys_prompt += msg.content.lower() + " "
                if msg.role == "user" and msg.content:
                    user_prompt_dec += msg.content.lower() + " "

            data = {"actions": []}
            ready_steps = []
            for action in [
                "customer.search",
                "quotation.create_draft",
                "invoice.generate",
                "observability.get_api_latency",
                "product.search",
                "pricing.calculate",
            ]:
                if f"type: {action}" in sys_prompt or f"type: {action}" in sys_prompt:
                    match = re.search(r"- id:\s*([^,]+),\s*type:\s*" + action, sys_prompt)
                    if match:
                        ready_steps.append((match.group(1), action))

            if not ready_steps:
                import structlog

                logger = structlog.get_logger(__name__)
                logger.error("HEURISTIC_REGEX_FAILED", sys_prompt=sys_prompt)
                if "customer.search" in sys_prompt:
                    ready_steps.append(("step_1", "customer.search"))
                elif "quotation.create_draft" in sys_prompt:
                    ready_steps.append(("step_2", "quotation.create_draft"))
                elif "invoice.generate" in sys_prompt:
                    ready_steps.append(("step_1", "invoice.generate"))

            for action_id, action_type in ready_steps:
                action_type = action_type.strip()
                if action_type == "customer.search":
                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {"query": "acme"},
                            "reasoning": "Search for customer.",
                        }
                    )
                elif action_type == "quotation.create_draft":
                    req_line = user_prompt_dec
                    if "original user request:" in user_prompt_dec:
                        req_line = user_prompt_dec.split("original user request:")[1].split("\n")[0]

                    cust_id_match = re.search(r'"id":\s*"([^"]+)"', user_prompt_dec)
                    if cust_id_match and not any(k in req_line for k in ["acme", "global", "nexa", "apex", "nova", "cloud infotech", "for "]):
                        cust_id = cust_id_match.group(1)
                        match_org = re.search(r"org_id[^a-z0-9]+([a-f0-9\-]{36})", sys_prompt + user_prompt_dec)
                        prod_id = f"PROD-X-{match_org.group(1)[:8]}" if match_org else "PROD-X"
                        data["actions"].append(
                            {
                                "action_id": action_id,
                                "arguments": {
                                    "customer_id": cust_id,
                                    "items": [{"product_id": prod_id, "quantity": 1}],
                                },
                                "reasoning": "Create quotation via customer ID.",
                            }
                        )
                    else:
                        company = "Acme Technologies"
                        model = "UC-2000-VE-4T"
                        tier = "end_customer"
                        qty = 1

                        for comp_key, comp_name in [
                            ("acme", "Acme Technologies"),
                            ("global", "Global Telecom Ltd"),
                            ("nexa", "Nexa Communications"),
                            ("apex", "Apex Enterprise"),
                            ("nova", "Nova Systems"),
                            ("cloud infotech", "Cloud Infotech Partner"),
                        ]:
                            if comp_key in req_line:
                                company = comp_name
                                break

                        for_match = re.search(r"for\s+([^,]+?)\s+for\s+\d+", req_line)
                        if for_match:
                            company = for_match.group(1).strip()

                        for mod_key in [
                            "uc-2000-ve-2t", "uc-2000-ve-4t", "uc-2000-ve-8t", "uc-2000-vf-16t", "uc-2000-vg-32t",
                            "dag1000-2s", "dag1000-4s", "dag1000-8s", "dag2000-16s", "dag2000-24s",
                            "dag1000-4s4o", "dag1000-8s8o", "uc120", "uc200", "sbc300-10", "sbc300-20",
                            "sbc1000-050", "sbc3000", "ent-db-001"
                        ]:
                            if mod_key in req_line:
                                model = mod_key.upper()
                                break

                        if "retail" in req_line:
                            tier = "retail"
                        elif "msp" in req_line:
                            tier = "msp"
                        elif "mrp" in req_line:
                            tier = "mrp"
                        elif "end_customer" in req_line or "end customer" in req_line:
                            tier = "end_customer"

                        qty_match = re.search(r'(?:qty|quantity)[:\s]+(\d+)|(\d+)\s*(?:units?|pcs?|nos?)', req_line)
                        if qty_match:
                            qty = max(1, int(qty_match.group(1) or qty_match.group(2)))

                        data["actions"].append(
                            {
                                "action_id": action_id,
                                "arguments": {
                                    "company_name": company,
                                    "model_number": model,
                                    "quantity": qty,
                                    "price_tier": tier,
                                },
                                "reasoning": "Create commercial quotation from Cloud Infotech catalog.",
                            }
                        )
                elif action_type == "invoice.generate":
                    company = "Acme Technologies"
                    model = "UC-2000-VE-4T"
                    tier = "end_customer"
                    qty = 1

                    req_line = user_prompt_dec
                    if "original user request:" in user_prompt_dec:
                        req_line = user_prompt_dec.split("original user request:")[1].split("\n")[0]

                    for comp_key, comp_name in [
                        ("acme", "Acme Technologies"),
                        ("global", "Global Telecom Ltd"),
                        ("nexa", "Nexa Communications"),
                        ("apex", "Apex Enterprise"),
                        ("nova", "Nova Systems"),
                        ("cloud infotech", "Cloud Infotech Partner"),
                    ]:
                        if comp_key in req_line:
                            company = comp_name
                            break

                    for mod_key in [
                        "uc-2000-ve-2t", "uc-2000-ve-4t", "uc-2000-ve-8t", "uc-2000-vf-16t", "uc-2000-vg-32t",
                        "dag1000-2s", "dag1000-4s", "dag1000-8s", "dag2000-16s", "dag2000-24s",
                        "dag1000-4s4o", "dag1000-8s8o", "uc120", "uc200", "sbc300-10", "sbc300-20",
                        "sbc1000-050", "sbc3000"
                    ]:
                        if mod_key in req_line:
                            model = mod_key.upper()
                            break

                    if "retail" in req_line:
                        tier = "retail"
                    elif "msp" in req_line:
                        tier = "msp"
                    elif "mrp" in req_line:
                        tier = "mrp"
                    elif "end_customer" in req_line or "end customer" in req_line:
                        tier = "end_customer"

                    qty_match = re.search(r'(?:qty|quantity)[:\s]+(\d+)|(\d+)\s*(?:units?|pcs?|nos?)', req_line)
                    if qty_match:
                        qty = max(1, int(qty_match.group(1) or qty_match.group(2)))

                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {
                                "company_name": company,
                                "model_number": model,
                                "quantity": qty,
                                "price_tier": tier,
                            },
                            "reasoning": "Generate official tax invoice from Cloud Infotech catalog.",
                        }
                    )
                elif action_type == "observability.get_api_latency":
                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {"time_range": "24h"},
                            "reasoning": "Retrieve latency metrics.",
                        }
                    )
                elif action_type == "product.search":
                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {"query": "demo"},
                            "reasoning": "Search for products.",
                        }
                    )
                elif action_type == "pricing.calculate":
                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {"product_id": "PROD-X", "quantity": 1},
                            "reasoning": "Calculate pricing.",
                        }
                    )

        elif schema.__name__ == "IntentUnderstanding":
            data = {
                "intent": "general_query",
                "entities": {},
                "confidence": 0.95,
                "normalized_request": user_prompt.strip() or "User request",
                "is_safe": True,
                "requires_clarification": False,
                "clarification_question": None,
                "reasoning": "Safe business query processed by AURA.",
            }

        else:
            from app.ai.errors.exceptions import LLMValidationError

            raise LLMValidationError(f"HeuristicProvider does not support schema {schema.__name__}")

        try:
            parsed = schema.model_validate(data)
        except Exception as e:
            from app.ai.errors.exceptions import LLMValidationError

            raise LLMValidationError(f"HeuristicProvider failed to validate generated data: {e}")

        result = GenerationResult(
            text=json.dumps(data),
            structured_data=data,
            model=request.model,
            provider=self.name,
            usage=Usage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
            finish_reason="stop",
            raw_response={"heuristic": True},
        )
        return result, parsed

    async def stream(self, request: GenerationRequest):
        text = (await self.generate(request)).text
        words = text.split(" ")
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i : i + chunk_size]) + " "
            await asyncio.sleep(0.04)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.5] * 1536 for _ in texts]
