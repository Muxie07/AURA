from typing import Any
from fastapi import APIRouter
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.api.deps import CurrentUserDep, DatabaseDep
from app.database.models import AgentRun, Conversation

router = APIRouter(prefix="/forecasting", tags=["forecasting"])

@router.get("/")
async def get_forecasting(current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    # Need to check if sufficient data exists for the current user's organization
    base_query = select(AgentRun).join(Conversation).where(
        Conversation.organization_id == current_user.organization_id
    )
    
    query = select(func.count(AgentRun.id)).select_from(base_query.subquery())
    result = await db.execute(query)
    total_runs = result.scalar() or 0

    if total_runs < 5:
        return {
            "has_sufficient_data": False,
            "message": "Insufficient historical data for reliable forecasting. Minimum 5 agent runs required.",
            "forecast": None
        }

    # Aggregate stats over the last 24h vs previous 24h
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    day_before = now - timedelta(days=2)

    # Last 24h
    q_24h = select(func.count(AgentRun.id), func.avg(AgentRun.latency_ms), func.sum(AgentRun.total_tokens_output)).join(Conversation).where(
        Conversation.organization_id == current_user.organization_id,
        AgentRun.started_at >= yesterday
    )
    res_24h = await db.execute(q_24h)
    count_24h, avg_lat_24h, sum_tokens_24h = res_24h.first()

    # Previous 24h
    q_prev = select(func.count(AgentRun.id), func.avg(AgentRun.latency_ms)).join(Conversation).where(
        Conversation.organization_id == current_user.organization_id,
        AgentRun.started_at >= day_before,
        AgentRun.started_at < yesterday
    )
    res_prev = await db.execute(q_prev)
    count_prev, avg_lat_prev = res_prev.first()
    
    # Calculate failure rates
    q_fail_24h = select(func.count(AgentRun.id)).join(Conversation).where(
        Conversation.organization_id == current_user.organization_id,
        AgentRun.started_at >= yesterday,
        AgentRun.status == 'failed'
    )
    res_fail_24h = await db.execute(q_fail_24h)
    fails_24h = res_fail_24h.scalar() or 0

    fail_rate = (fails_24h / count_24h) if count_24h else 0

    cost_today = float(count_24h or 0) * 0.001  # Mock estimation, ideally from cost manager

    return {
        "has_sufficient_data": True,
        "message": "Forecast generated using active telemetry.",
        "forecast": {
            "next_24h": {
                "expected_volume": max(int((count_24h or 0) * 1.1), 5),
                "expected_latency_trend": "stable" if avg_lat_24h and avg_lat_prev and abs(avg_lat_24h - avg_lat_prev) < 200 else "degrading",
                "expected_error_rate": f"{fail_rate * 100:.1f}%",
                "capacity_concern": count_24h > 1000
            },
            "cost": {
                "today_usd": cost_today,
                "projected_7d_usd": cost_today * 7 * 1.05,
                "projected_30d_usd": cost_today * 30 * 1.1
            },
            "latency": {
                "current_ms": float(avg_lat_24h or 1500),
                "trend": "up" if avg_lat_24h and avg_lat_prev and avg_lat_24h > avg_lat_prev else "down"
            },
            "failures": {
                "current_rate": fail_rate,
                "trend": "stable",
                "risk": "low" if fail_rate < 0.05 else "high"
            }
        }
    }
