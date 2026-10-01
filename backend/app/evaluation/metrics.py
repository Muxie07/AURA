"""
AURA Phase 9 — Ops Metrics Collector.

Aggregates AI Operations metrics for the observability dashboard.
All aggregations are tenant-isolated. No cross-org data leakage.
"""
from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.schemas import OpsMetrics

logger = structlog.get_logger(__name__)


class OpsMetricsCollector:
    """
    Collects and aggregates AI Operations metrics for an organization.
    Enforces strict tenant isolation on all queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect(
        self,
        organization_id: uuid.UUID,
        window_hours: int = 24,
    ) -> OpsMetrics:
        """
        Collect aggregated metrics for an org over the given time window.
        Returns OpsMetrics with tenant-isolated data.
        """
        metrics = OpsMetrics(
            organization_id=organization_id,
            window_hours=window_hours,
        )

        try:
            # Run metrics from agent_runs table
            run_stats = await self._collect_run_stats(organization_id, window_hours)
            metrics.total_runs = run_stats.get("total", 0)
            metrics.successful_runs = run_stats.get("success", 0)
            metrics.failed_runs = run_stats.get("failed", 0)
            metrics.success_rate = (
                metrics.successful_runs / metrics.total_runs
                if metrics.total_runs > 0 else 0.0
            )
            metrics.avg_latency_ms = run_stats.get("avg_latency_ms", 0.0)
            metrics.total_tokens = run_stats.get("total_tokens", 0)
            metrics.total_cost_usd = run_stats.get("total_cost_usd", 0.0)

            # Tool usage from tool_call_logs
            tool_usage = await self._collect_tool_usage(organization_id, window_hours)
            metrics.tool_usage = tool_usage

            # Approval metrics
            approval_stats = await self._collect_approval_stats(organization_id, window_hours)
            metrics.pending_approvals = approval_stats.get("pending", 0)
            metrics.policy_blocks = approval_stats.get("denied", 0)

        except Exception as e:
            logger.warning("ops_metrics_collection_failed", error=str(e), org=str(organization_id))

        return metrics

    async def _collect_run_stats(
        self, organization_id: uuid.UUID, window_hours: int
    ) -> dict[str, Any]:
        """Collect agent run statistics — tenant isolated."""
        try:
            stmt = sa.text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as success,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
                    COALESCE(SUM(token_count), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0) as total_cost_usd
                FROM agent_runs
                WHERE organization_id = :org_id
                  AND started_at >= NOW() - INTERVAL ':hours hours'
            """)
            result = await self.db.execute(stmt, {
                "org_id": str(organization_id),
                "hours": window_hours,
            })
            row = result.fetchone()
            if row:
                return {
                    "total": row[0] or 0,
                    "success": row[1] or 0,
                    "failed": row[2] or 0,
                    "avg_latency_ms": float(row[3] or 0),
                    "total_tokens": int(row[4] or 0),
                    "total_cost_usd": float(row[5] or 0),
                }
        except Exception as e:
            logger.debug("run_stats_query_failed", error=str(e))
        return {}

    async def _collect_tool_usage(
        self, organization_id: uuid.UUID, window_hours: int
    ) -> dict[str, int]:
        """Collect tool usage counts — tenant isolated."""
        try:
            stmt = sa.text("""
                SELECT tool_name, COUNT(*) as usage_count
                FROM tool_call_logs
                WHERE organization_id = :org_id
                  AND created_at >= NOW() - INTERVAL ':hours hours'
                GROUP BY tool_name
                ORDER BY usage_count DESC
                LIMIT 20
            """)
            result = await self.db.execute(stmt, {
                "org_id": str(organization_id),
                "hours": window_hours,
            })
            return {row[0]: int(row[1]) for row in result.fetchall()}
        except Exception as e:
            logger.debug("tool_usage_query_failed", error=str(e))
        return {}

    async def _collect_approval_stats(
        self, organization_id: uuid.UUID, window_hours: int
    ) -> dict[str, int]:
        """Collect approval request stats — tenant isolated."""
        try:
            stmt = sa.text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE status = 'denied') as denied
                FROM approval_requests ar
                JOIN agent_runs r ON ar.agent_run_id = r.id
                WHERE r.organization_id = :org_id
                  AND ar.created_at >= NOW() - INTERVAL ':hours hours'
            """)
            result = await self.db.execute(stmt, {
                "org_id": str(organization_id),
                "hours": window_hours,
            })
            row = result.fetchone()
            if row:
                return {"pending": int(row[0] or 0), "denied": int(row[1] or 0)}
        except Exception as e:
            logger.debug("approval_stats_query_failed", error=str(e))
        return {}
