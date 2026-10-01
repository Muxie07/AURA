"""
AURA Phase 9 — Evaluation Schemas.

Defines pydantic models for agent evaluation results, quality scores,
safety scores, cost tracking, and benchmark results.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class EvaluationDimension(BaseModel):
    """A single evaluation dimension with score and explanation."""

    name: str
    score: float = Field(ge=0.0, le=1.0)
    status: EvaluationStatus
    evidence: str = ""
    weight: float = Field(default=1.0, ge=0.0)


class SafetyScore(BaseModel):
    """Run-level safety evaluation."""

    run_id: uuid.UUID
    organization_id: uuid.UUID
    overall_score: float = Field(ge=0.0, le=1.0)  # 1.0 = safest
    policy_violations: int = 0
    unauthorized_tool_attempts: int = 0
    prompt_injection_detected: bool = False
    tenant_boundary_violations: int = 0
    failed_verifications: int = 0
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    details: list[EvaluationDimension] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QualityScore(BaseModel):
    """Agent run quality evaluation."""

    run_id: uuid.UUID
    organization_id: uuid.UUID
    overall_score: float = Field(ge=0.0, le=1.0)
    task_success: float = Field(ge=0.0, le=1.0, default=0.0)
    tool_selection_accuracy: float = Field(ge=0.0, le=1.0, default=0.0)
    retrieval_quality: float = Field(ge=0.0, le=1.0, default=0.0)
    citation_correctness: float = Field(ge=0.0, le=1.0, default=0.0)
    policy_compliance: float = Field(ge=0.0, le=1.0, default=0.0)
    cost_efficiency: float = Field(ge=0.0, le=1.0, default=0.0)
    latency_score: float = Field(ge=0.0, le=1.0, default=0.0)
    dimensions: list[EvaluationDimension] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CostEstimate(BaseModel):
    """Per-model cost configuration and estimation."""

    model: str
    provider: str
    input_cost_per_1k_tokens: float  # USD
    output_cost_per_1k_tokens: float  # USD
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def calculate(self) -> CostEstimate:
        self.estimated_cost_usd = (self.input_tokens / 1000) * self.input_cost_per_1k_tokens + (
            self.output_tokens / 1000
        ) * self.output_cost_per_1k_tokens
        return self


class BudgetStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


class BudgetCheck(BaseModel):
    """Result of a budget enforcement check."""

    run_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    estimated_cost_usd: float
    per_run_budget_usd: float | None = None
    org_daily_budget_usd: float | None = None
    org_daily_spend_usd: float = 0.0
    status: BudgetStatus = BudgetStatus.OK
    message: str = ""


class GoldenExample(BaseModel):
    """A single golden dataset example for evaluation."""

    id: str
    category: str  # customer, quotation, knowledge, tool_selection, security
    input: str
    expected_tools: list[str] = Field(default_factory=list)
    expected_output_contains: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    is_attack: bool = False
    attack_type: str | None = None


class BenchmarkResult(BaseModel):
    """Result of a benchmark run for a single model."""

    model: str
    provider: str
    task_type: str
    success_rate: float = Field(ge=0.0, le=1.0)
    avg_latency_ms: float
    avg_tokens: float
    avg_cost_usd: float
    sample_count: int
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentRecord(BaseModel):
    """An incident log record for agent failures and security events."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    severity: IncidentSeverity
    category: str  # agent_failure, security, policy_violation, tool_error, model_failure
    title: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False


class OpsMetrics(BaseModel):
    """Aggregated AI Operations metrics for the dashboard."""

    organization_id: uuid.UUID
    window_hours: int = 24
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    model_distribution: dict[str, int] = Field(default_factory=dict)
    tool_usage: dict[str, int] = Field(default_factory=dict)
    policy_blocks: int = 0
    pending_approvals: int = 0
    avg_retrieval_quality: float = 0.0
    incident_count: int = 0
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
