import uuid
from datetime import UTC, datetime
from typing import ClassVar

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.models import LLMUsage
from app.evaluation.schemas import BudgetCheck, BudgetStatus, CostEstimate

logger = structlog.get_logger(__name__)

# Model cost table (USD per 1M tokens, input/output)
MODEL_COST_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-3.5-turbo": (0.50, 1.50),
    "claude-3-5-sonnet-20241022": (3.0, 15.0),
    "claude-3-haiku-20240307": (0.25, 1.25),
    "gemini-1.5-pro": (1.25, 5.0),
    "gemini-1.5-flash": (0.075, 0.30),
    "default": (2.0, 8.0),
}

DEFAULT_PER_RUN_BUDGET_USD = 0.50
DEFAULT_ORG_DAILY_BUDGET_USD = 50.0
DEFAULT_ORG_MONTHLY_BUDGET_USD = 1000.0

LUA_SCRIPT = """
local daily_key = KEYS[1]
local monthly_key = KEYS[2]
local amount = tonumber(ARGV[1])
local daily_limit = tonumber(ARGV[2])
local monthly_limit = tonumber(ARGV[3])

local current_daily = tonumber(redis.call('GET', daily_key) or '0')
local current_monthly = tonumber(redis.call('GET', monthly_key) or '0')

if (current_daily + amount) > daily_limit then
    return {0, current_daily, current_monthly, 'DAILY_EXCEEDED'}
end
if (current_monthly + amount) > monthly_limit then
    return {0, current_daily, current_monthly, 'MONTHLY_EXCEEDED'}
end

local new_daily = redis.call('INCRBYFLOAT', daily_key, amount)
local new_monthly = redis.call('INCRBYFLOAT', monthly_key, amount)

if current_daily == 0 then
    redis.call('EXPIRE', daily_key, 86400)
end
if current_monthly == 0 then
    redis.call('EXPIRE', monthly_key, 2592000)
end

return {1, tonumber(new_daily), tonumber(new_monthly), 'OK'}
"""

class CostManager:
    _redis_client: ClassVar[aioredis.Redis | None] = None
    _script_sha: ClassVar[str | None] = None

    @classmethod
    async def get_redis(cls) -> aioredis.Redis:
        if cls._redis_client is None:
            settings = get_settings()
            cls._redis_client = aioredis.from_url(settings.redis_url, socket_timeout=2.0)
        return cls._redis_client

    @classmethod
    def get_model_costs(cls, model: str) -> tuple[float, float]:
        """Return (input_cost_per_1M, output_cost_per_1M) for a model."""
        return MODEL_COST_TABLE.get(model, MODEL_COST_TABLE["default"])

    @classmethod
    def estimate_cost(
        cls,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        in_1m, out_1m = cls.get_model_costs(model)
        # Convert to per 1k for backwards compatibility in schemas if needed
        estimate = CostEstimate(
            model=model,
            provider=provider,
            input_cost_per_1k_tokens=in_1m / 1000.0,
            output_cost_per_1k_tokens=out_1m / 1000.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return estimate.calculate()

    @classmethod
    async def check_budget_async(
        cls,
        organization_id: uuid.UUID,
        estimated_cost_usd: float,
        run_id: uuid.UUID | None = None,
    ) -> BudgetCheck:
        redis = await cls.get_redis()
        org_key = str(organization_id)

        now = datetime.now(UTC)
        daily_key = f"budget:daily:{org_key}:{now.strftime('%Y%m%d')}"
        monthly_key = f"budget:monthly:{org_key}:{now.strftime('%Y%m')}"

        try:
            res = await redis.eval(
                LUA_SCRIPT,
                2,
                daily_key,
                monthly_key,
                estimated_cost_usd,
                DEFAULT_ORG_DAILY_BUDGET_USD,
                DEFAULT_ORG_MONTHLY_BUDGET_USD
            )
            success, daily_spend, _monthly_spend, msg = res
            status = BudgetStatus.OK
            message = "Within budget"

            if not success:
                status = BudgetStatus.EXCEEDED
                message = f"Budget exceeded: {msg.decode('utf-8')}"

            return BudgetCheck(
                run_id=run_id,
                organization_id=organization_id,
                estimated_cost_usd=estimated_cost_usd,
                per_run_budget_usd=DEFAULT_PER_RUN_BUDGET_USD,
                org_daily_budget_usd=DEFAULT_ORG_DAILY_BUDGET_USD,
                org_daily_spend_usd=float(daily_spend),
                status=status,
                message=message
            )
        except Exception as e:
            logger.error("redis_budget_check_failed", error=str(e))
            # Fail open if redis is down
            return BudgetCheck(
                run_id=run_id,
                organization_id=organization_id,
                estimated_cost_usd=estimated_cost_usd,
                per_run_budget_usd=DEFAULT_PER_RUN_BUDGET_USD,
                org_daily_budget_usd=DEFAULT_ORG_DAILY_BUDGET_USD,
                org_daily_spend_usd=0.0,
                status=BudgetStatus.OK,
                message="Fallback allow"
            )

    @classmethod
    async def record_usage_async(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        agent_run_id: uuid.UUID | None,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
    ) -> None:
        usage = LLMUsage(
            id=uuid.uuid4(),
            organization_id=organization_id,
            agent_run_id=agent_run_id,
            provider=provider,
            model=model,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            cost_usd=total_cost,
        )
        db.add(usage)
        await db.commit()

    @classmethod
    async def reset_daily_spend(cls, organization_id: uuid.UUID) -> None:
        redis = await cls.get_redis()
        now = datetime.now(UTC)
        org_key = str(organization_id)
        daily_key = f"budget:daily:{org_key}:{now.strftime('%Y%m%d')}"
        monthly_key = f"budget:monthly:{org_key}:{now.strftime('%Y%m')}"
        await redis.delete(daily_key, monthly_key)
