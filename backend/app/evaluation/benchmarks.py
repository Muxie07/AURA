"""
AURA Phase 9 — Benchmarking Engine.

Provides deterministic model benchmarking without live LLM calls.
Uses pre-computed mock results for test environments.
"""
from __future__ import annotations

from app.evaluation.schemas import BenchmarkResult

# Pre-computed benchmark reference data (deterministic, no LLM needed)
BENCHMARK_REFERENCE: list[BenchmarkResult] = [
    BenchmarkResult(
        model="gpt-4o-mini",
        provider="openai",
        task_type="SIMPLE_CLASSIFICATION",
        success_rate=0.91,
        avg_latency_ms=450.0,
        avg_tokens=350.0,
        avg_cost_usd=0.000105,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4o",
        provider="openai",
        task_type="SIMPLE_CLASSIFICATION",
        success_rate=0.97,
        avg_latency_ms=1200.0,
        avg_tokens=380.0,
        avg_cost_usd=0.00095,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4-turbo",
        provider="openai",
        task_type="SIMPLE_CLASSIFICATION",
        success_rate=0.96,
        avg_latency_ms=1800.0,
        avg_tokens=390.0,
        avg_cost_usd=0.0039,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4o-mini",
        provider="openai",
        task_type="COMPLEX_REASONING",
        success_rate=0.72,
        avg_latency_ms=780.0,
        avg_tokens=1200.0,
        avg_cost_usd=0.00036,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4o",
        provider="openai",
        task_type="COMPLEX_REASONING",
        success_rate=0.94,
        avg_latency_ms=2100.0,
        avg_tokens=1400.0,
        avg_cost_usd=0.0035,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4-turbo",
        provider="openai",
        task_type="COMPLEX_REASONING",
        success_rate=0.93,
        avg_latency_ms=2800.0,
        avg_tokens=1500.0,
        avg_cost_usd=0.015,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4o-mini",
        provider="openai",
        task_type="TOOL_USE",
        success_rate=0.83,
        avg_latency_ms=650.0,
        avg_tokens=800.0,
        avg_cost_usd=0.00024,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4o",
        provider="openai",
        task_type="TOOL_USE",
        success_rate=0.96,
        avg_latency_ms=1500.0,
        avg_tokens=900.0,
        avg_cost_usd=0.00225,
        sample_count=100,
    ),
    BenchmarkResult(
        model="gpt-4-turbo",
        provider="openai",
        task_type="LONG_CONTEXT",
        success_rate=0.95,
        avg_latency_ms=4200.0,
        avg_tokens=8000.0,
        avg_cost_usd=0.08,
        sample_count=50,
    ),
]


class BenchmarkEngine:
    """
    Provides model benchmark comparisons.
    In production, would run actual eval runs.
    For deterministic testing, uses pre-computed reference data.
    """

    @staticmethod
    def get_benchmark(model: str, task_type: str) -> BenchmarkResult | None:
        """Get benchmark result for a specific model and task type."""
        for result in BENCHMARK_REFERENCE:
            if result.model == model and result.task_type == task_type:
                return result
        return None

    @staticmethod
    def compare_models(task_type: str) -> list[BenchmarkResult]:
        """Compare all models for a given task type, sorted by efficiency."""
        results = [r for r in BENCHMARK_REFERENCE if r.task_type == task_type]
        # Sort by cost-adjusted success rate (value for money)
        return sorted(
            results,
            key=lambda r: r.success_rate / (r.avg_cost_usd + 0.00001),
            reverse=True,
        )

    @staticmethod
    def recommend_model(
        task_type: str,
        min_success_rate: float = 0.85,
        max_cost_usd: float = 0.01,
    ) -> BenchmarkResult | None:
        """
        Recommend the cheapest model meeting quality and cost thresholds.
        This is the core of cost-intelligent model routing.
        """
        candidates = [
            r for r in BENCHMARK_REFERENCE
            if r.task_type == task_type
            and r.success_rate >= min_success_rate
            and r.avg_cost_usd <= max_cost_usd
        ]
        if not candidates:
            # Relax cost constraint, just get highest success rate
            candidates = [
                r for r in BENCHMARK_REFERENCE
                if r.task_type == task_type
                and r.success_rate >= min_success_rate
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda r: r.avg_cost_usd)

    @staticmethod
    def get_all_benchmarks() -> list[BenchmarkResult]:
        return list(BENCHMARK_REFERENCE)
