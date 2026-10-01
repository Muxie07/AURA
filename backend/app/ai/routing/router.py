from typing import Any, Literal, cast

from pydantic import BaseModel

from app.ai.errors.exceptions import ModelRoutingError
from app.config.settings import get_settings


class TaskProfile(BaseModel):
    task_type: Literal[
        "SIMPLE_CLASSIFICATION",
        "INFORMATION_EXTRACTION",
        "RAG_QUESTION",
        "COMPLEX_REASONING",
        "TOOL_USE",
        "STRUCTURED_GENERATION",
        "LONG_CONTEXT",
        "GENERAL_CHAT"
    ]
    complexity: Literal["LOW", "MEDIUM", "HIGH"]
    requires_tools: bool
    requires_rag: bool
    requires_structured_output: bool
    context_length: int
    latency_requirement: Literal["LOW", "HIGH"]
    cost_sensitivity: Literal["LOW", "HIGH"]

class ModelSelection(BaseModel):
    provider: str
    model: str
    fallback_model: str | None
    reason: str
    estimated_cost: str
    expected_latency: str
    capabilities: list[str]

class ModelRouter:
    """
    Intelligent model router abstraction.
    Classifies tasks and selects the appropriate model and fallback.
    """

    @staticmethod
    def classify_task(prompt: str, has_tools: bool = False, has_rag: bool = False) -> TaskProfile:
        prompt_len = len(prompt)
        context_length = prompt_len

        if prompt_len > 8000:
            task_type = "LONG_CONTEXT"
            complexity = "HIGH"
            latency_requirement = "LOW"
            cost_sensitivity = "LOW"
        elif has_tools:
            task_type = "TOOL_USE"
            complexity = "HIGH"
            latency_requirement = "LOW"
            cost_sensitivity = "LOW"
        elif has_rag:
            task_type = "RAG_QUESTION"
            complexity = "MEDIUM"
            latency_requirement = "LOW"
            cost_sensitivity = "LOW"
        else:
            task_type = "GENERAL_CHAT"
            complexity = "LOW"
            latency_requirement = "HIGH"
            cost_sensitivity = "HIGH"

        return TaskProfile(
            task_type=cast(Any, task_type),
            complexity=cast(Any, complexity),
            requires_tools=has_tools,
            requires_rag=has_rag,
            requires_structured_output=False,
            context_length=context_length,
            latency_requirement=cast(Any, latency_requirement),
            cost_sensitivity=cast(Any, cost_sensitivity)
        )

    @staticmethod
    def route_task(profile: TaskProfile) -> ModelSelection:
        settings = get_settings()
        if not settings.primary_llm_model:
            raise ModelRoutingError('No default model configured.')

        from app.evaluation.benchmarks import BenchmarkEngine

        selected_model = settings.fast_model
        fallback_model = settings.reasoning_model
        reason = 'Default fast model'

        min_success_rate = 0.90 if profile.complexity == "HIGH" else 0.85
        max_cost_usd = 0.005 if profile.cost_sensitivity == "HIGH" else 0.05

        if profile.task_type == 'LONG_CONTEXT' or profile.context_length > 8000:
            selected_model = settings.long_context_model
            reason = 'Selected long context model due to large prompt length.'
        else:
            try:
                rec = BenchmarkEngine.recommend_model(
                    task_type=profile.task_type,
                    min_success_rate=min_success_rate,
                    max_cost_usd=max_cost_usd
                )
                if rec and rec.provider == settings.primary_llm_provider.value:
                    selected_model = rec.model
                    reason = 'Selected cheapest model meeting quality threshold.'
                else:
                    if profile.complexity == 'HIGH' or profile.requires_tools:
                        selected_model = settings.reasoning_model
                        reason = 'Heuristic: Selected reasoning model.'
            except Exception:
                if profile.complexity == 'HIGH' or profile.requires_tools:
                    selected_model = settings.reasoning_model
                    reason = 'Heuristic: Selected reasoning model.'

        return ModelSelection(
            provider=settings.primary_llm_provider.value,
            model=selected_model,
            fallback_model=fallback_model,
            reason=reason,
            estimated_cost='low',
            expected_latency='low',
            capabilities=['chat', 'tools'] if profile.requires_tools else ['chat']
        )

    @classmethod
    def get_model_for_task(cls, task: str) -> str:
        """Legacy compatibility method."""
        profile = cls.classify_task(task)
        selection = cls.route_task(profile)
        return selection.model
