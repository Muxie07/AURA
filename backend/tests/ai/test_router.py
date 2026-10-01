from typing import Any

from app.ai.routing.router import ModelRouter, TaskProfile
from app.config.settings import get_settings


def test_model_router_benchmark(monkeypatch: Any) -> None:
    monkeypatch.setenv("FAST_MODEL", "test-fast")
    monkeypatch.setenv("REASONING_MODEL", "test-reason")
    monkeypatch.setenv("LONG_CONTEXT_MODEL", "test-long")
    get_settings.cache_clear()

    # 1. Simple classification -> Cheap model (gpt-4o-mini)
    profile = TaskProfile(
        task_type="SIMPLE_CLASSIFICATION",
        complexity="LOW",
        requires_tools=False,
        requires_rag=False,
        requires_structured_output=False,
        context_length=100,
        latency_requirement="HIGH",
        cost_sensitivity="HIGH"
    )
    sel = ModelRouter.route_task(profile)
    # the router now uses settings.fast_model (test-fast) if the benchmark provider does not match the system provider.
    assert sel.model in ["gpt-4o-mini", "test-fast"]

    # 2. Complex reasoning -> reasoning model that meets high success rate
    profile = TaskProfile(
        task_type="COMPLEX_REASONING",
        complexity="HIGH",
        requires_tools=False,
        requires_rag=False,
        requires_structured_output=True,
        context_length=1000,
        latency_requirement="LOW",
        cost_sensitivity="LOW"
    )
    sel = ModelRouter.route_task(profile)
    assert sel.model in ["gpt-4o", "test-reason"]

    # 3. Long context -> LONG_CONTEXT_MODEL
    profile = TaskProfile(
        task_type="LONG_CONTEXT",
        complexity="MEDIUM",
        requires_tools=False,
        requires_rag=True,
        requires_structured_output=False,
        context_length=50000,
        latency_requirement="LOW",
        cost_sensitivity="LOW"
    )
    sel = ModelRouter.route_task(profile)
    assert sel.model == "test-long"
