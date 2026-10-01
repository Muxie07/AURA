"""
AURA Phase 9 — Cost Manager.

Provides model cost configuration, token budget enforcement,
and per-run cost estimation. Prevents runaway AI spending.
"""
from __future__ import annotations

import uuid
from typing import ClassVar

import structlog

from app.evaluation.schemas import BudgetCheck, BudgetStatus, CostEstimate

logger = structlog.get_logger(__name__)

# Model cost table (USD per 1000 tokens, input/output)
MODEL_COST_TABLE: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o":           (0.0025, 0.0100),
    "gpt-4o-mini":      (0.00015, 0.00060),
    "gpt-4-turbo":      (0.0100, 0.0300),
    "gpt-3.5-turbo":    (0.00050, 0.00150),
    # Anthropic
    "claude-3-5-sonnet-20241022": (0.0030, 0.0150),
    "claude-3-haiku-20240307":    (0.00025, 0.00125),
    # Google
    "gemini-1.5-pro":   (0.00125, 0.00500),
    "gemini-1.5-flash": (0.000075, 0.00030),
    # Fallback for unknown models
    "default":          (0.002, 0.008),
}

# Default per-run budget: $0.50 USD
DEFAULT_PER_RUN_BUDGET_USD = 0.50
# Default daily org budget: $50 USD
DEFAULT_ORG_DAILY_BUDGET_USD = 50.0


class CostManager:
    """
    Manages cost estimation and budget enforcement for AI operations.
    All costs are in USD.
    """

    _org_daily_spend: ClassVar[dict[str, float]] = {}  # org_id -> spend today

    @classmethod
    def get_model_costs(cls, model: str) -> tuple[float, float]:
        """Return (input_cost_per_1k, output_cost_per_1k) for a model."""
        return MODEL_COST_TABLE.get(model, MODEL_COST_TABLE["default"])

    @classmethod
    def estimate_cost(
        cls,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """Estimate cost for a given number of tokens."""
        input_cost_per_1k, output_cost_per_1k = cls.get_model_costs(model)
        estimate = CostEstimate(
            model=model,
            provider=provider,
            input_cost_per_1k_tokens=input_cost_per_1k,
            output_cost_per_1k_tokens=output_cost_per_1k,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return estimate.calculate()

    @classmethod
    def check_budget(
        cls,
        organization_id: uuid.UUID,
        estimated_cost_usd: float,
        run_id: uuid.UUID | None = None,
        per_run_budget_usd: float | None = None,
        org_daily_budget_usd: float | None = None,
    ) -> BudgetCheck:
        """
        Check if a run is within budget constraints.
        Returns a BudgetCheck with status OK, WARNING, or EXCEEDED.
        """
        per_run_budget = per_run_budget_usd or DEFAULT_PER_RUN_BUDGET_USD
        org_daily_budget = org_daily_budget_usd or DEFAULT_ORG_DAILY_BUDGET_USD

        org_key = str(organization_id)
        org_daily_spend = cls._org_daily_spend.get(org_key, 0.0)

        status = BudgetStatus.OK
        message = "Within budget."

        if estimated_cost_usd > per_run_budget:
            status = BudgetStatus.EXCEEDED
            message = (
                f"Estimated cost ${estimated_cost_usd:.4f} exceeds per-run "
                f"budget ${per_run_budget:.2f}."
            )
        elif (org_daily_spend + estimated_cost_usd) > org_daily_budget:
            status = BudgetStatus.EXCEEDED
            message = (
                f"Organization daily spend ${org_daily_spend:.2f} + "
                f"estimated ${estimated_cost_usd:.4f} would exceed daily "
                f"budget ${org_daily_budget:.2f}."
            )
        elif estimated_cost_usd > per_run_budget * 0.8:
            status = BudgetStatus.WARNING
            message = f"Cost ${estimated_cost_usd:.4f} approaching per-run budget limit."

        if status != BudgetStatus.EXCEEDED:
            # Reserve the spend
            cls._org_daily_spend[org_key] = org_daily_spend + estimated_cost_usd

        logger.info(
            "budget_check",
            org=org_key,
            estimated=estimated_cost_usd,
            status=status,
        )

        return BudgetCheck(
            run_id=run_id,
            organization_id=organization_id,
            estimated_cost_usd=estimated_cost_usd,
            per_run_budget_usd=per_run_budget,
            org_daily_budget_usd=org_daily_budget,
            org_daily_spend_usd=org_daily_spend,
            status=status,
            message=message,
        )

    @classmethod
    def record_actual_spend(cls, organization_id: uuid.UUID, actual_cost_usd: float) -> None:
        """Record actual spend after run completion."""
        org_key = str(organization_id)
        cls._org_daily_spend[org_key] = cls._org_daily_spend.get(org_key, 0.0) + actual_cost_usd

    @classmethod
    def get_org_daily_spend(cls, organization_id: uuid.UUID) -> float:
        """Get current daily spend for an organization."""
        return cls._org_daily_spend.get(str(organization_id), 0.0)

    @classmethod
    def reset_daily_spend(cls, organization_id: uuid.UUID | None = None) -> None:
        """Reset daily spend (for testing or daily cron reset)."""
        if organization_id:
            cls._org_daily_spend.pop(str(organization_id), None)
        else:
            cls._org_daily_spend.clear()
