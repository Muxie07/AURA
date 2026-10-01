import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.providers.base import LLMProvider
from app.ai.schemas.generation import GenerationRequest, GenerationResult
from app.ai.schemas.usage import Usage

T = TypeVar("T", bound=BaseModel)

class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for testing."""

    @property
    def name(self) -> str:
        return "mock"

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        # Simple deterministic behavior for tests
        prompt = request.messages[-1].content if request.messages else ""

        response_text = "Mock response"
        if "2 + 2" in prompt:
            response_text = "4"
        elif "Explain what AURA does" in prompt:
            response_text = "AURA is an autonomous AI business operations engineer."

        return GenerationResult(
            text=response_text,
            model=request.model,
            provider=self.name,
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
            raw_response={"mocked": True}
        )

    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:

        # Default mock structured response
        mock_data: dict[str, Any] = {}
        if schema.__name__ == "IntentResult":
            mock_data = {"intent": "general_inquiry", "confidence": 0.97}
        elif schema.__name__ == "DecisionSchema":
            mock_data = {
                "actions": [
                    {
                        "action_id": "step_1",
                        "arguments": {"query": "John Doe"},
                        "reasoning": "Search for the customer"
                    }
                ]
            }
        elif schema.__name__ == "StructuredAgentPlan":
            mock_data = {
                "goal": "Search for customer",
                "steps": [
                    {
                        "id": "step_1",
                        "type": "customer.search",
                        "description": "Search for customer John Doe",
                        "dependencies": [],
                        "required_tools": ["customer.search"],
                        "risk": "LOW",
                        "expected_output": "Customer details",
                        "verification_criteria": "None",
                        "status": "pending"
                    }
                ]
            }
        elif schema.__name__ == "AgentRunSummary":
            mock_data = {
                "plan": {"goal": "Tell a short joke", "steps": []},
                "iterations": 1,
                "tool_calls_made": 0
            }

        parsed = schema.model_validate(mock_data)

        result = GenerationResult(
            text=json.dumps(mock_data),
            structured_data=mock_data,
            model=request.model,
            provider=self.name,
            usage=Usage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
            finish_reason="stop",
            raw_response={"mocked": True}
        )
        return result, parsed

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # noqa: ARG002
        chunks = ["Mock", " response", " streaming", "..."]
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.01)

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:  # noqa: ARG002
        # Return a deterministic 1536-dimensional vector for each text
        return [[0.1] * 1536 for _ in texts]
