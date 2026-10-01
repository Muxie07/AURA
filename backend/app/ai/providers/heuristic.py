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
        prompt = request.messages[-1].content.lower() if request.messages else ""

        text = "I'm currently operating in offline fallback mode. "
        if "quotation" in prompt:
            text += "I can help you create a draft quotation."
        elif "customer" in prompt:
            text += "I can help you search for customer information."
        elif "product" in prompt:
            text += "I can help you search for products."
        elif "pricing" in prompt:
            text += "I can help you calculate pricing."
        elif "latency" in prompt:
            text += "I can help you investigate API latency."
        else:
            text += "How can I assist you with your operations today?"

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
            if "quotation" in user_prompt:
                data = {
                    "goal": "Create a draft quotation",
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
                        },
                        {
                            "id": "step_2",
                            "type": "quotation.create_draft",
                            "description": "Create a new quotation draft",
                            "dependencies": ["step_1"],
                            "required_tools": ["quotation.create_draft"],
                            "risk": "HIGH",
                            "expected_output": "Quotation created successfully",
                            "verification_criteria": "None",
                            "status": "pending",
                        },
                    ],
                }
            elif "latency" in prompt or "observability" in prompt:
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
            elif "product" in prompt:
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
            elif "pricing" in prompt:
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
            elif "customer" in prompt:
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
                    cust_id = "unknown"
                    org_id = ""
                    match = re.search(r'"id":\s*"([^"]+)"', user_prompt_dec)
                    if match:
                        cust_id = match.group(1)
                    else:
                        match_org = re.search(
                            r"org_id[^a-z0-9]+([a-f0-9\-]{36})", sys_prompt + user_prompt_dec
                        )
                        if match_org:
                            org_id = match_org.group(1)
                            cust_id = f"CUST-001-{org_id[:8]}"
                    match_org2 = re.search(
                        r"org_id[^a-z0-9]+([a-f0-9\-]{36})", sys_prompt + user_prompt_dec
                    )
                    prod_id = f"PROD-X-{match_org2.group(1)[:8]}" if match_org2 else "PROD-X"

                    data["actions"].append(
                        {
                            "action_id": action_id,
                            "arguments": {
                                "customer_id": cust_id,
                                "items": [{"product_id": prod_id, "quantity": 1}],
                            },
                            "reasoning": "Create quotation.",
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
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.5] * 1536 for _ in texts]
