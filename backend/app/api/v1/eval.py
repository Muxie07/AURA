"""
AURA Phase 9 — Evaluation API Router.

Exposes evaluation, metrics, benchmarks, incidents, and replay endpoints.
All endpoints enforce strict tenant isolation via JWT org claims.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, DatabaseDep
from sqlalchemy import select, func
from app.database.models import EvalDataset, EvalExample, EvalRun, EvalResult
from app.evaluation.benchmarks import BenchmarkEngine
from app.evaluation.cost import CostManager
from app.evaluation.datasets import (
    ALL_GOLDEN_EXAMPLES,
    get_examples_by_category,
)
from app.evaluation.engine import (
    GoldenDatasetEvaluator,
    IncidentLogger,
    QualityEvaluator,
    SafetyEvaluator,
)
from app.evaluation.replay import ReplayEngine
from app.evaluation.schemas import (
    BudgetStatus,
    IncidentSeverity,
    OpsMetrics,
    QualityScore,
    SafetyScore,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/eval", tags=["AI Operations"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class EvaluateSafetyRequest(BaseModel):
    run_id: uuid.UUID
    organization_id: uuid.UUID
    policy_violations: int = 0
    unauthorized_tool_attempts: int = 0
    prompt_injection_attempts: list[str] = Field(default_factory=list)
    tenant_boundary_violations: int = 0
    failed_verifications: int = 0


class EvaluateQualityRequest(BaseModel):
    run_id: uuid.UUID
    organization_id: uuid.UUID
    succeeded: bool
    expected_tools: list[str] = Field(default_factory=list)
    actual_tools_used: list[str] = Field(default_factory=list)
    retrieved_chunks: int = 0
    cited_chunks: int = 0
    policy_compliant: bool = True
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class CostEstimateRequest(BaseModel):
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    organization_id: uuid.UUID
    run_id: uuid.UUID | None = None
    per_run_budget_usd: float | None = None


class GoldenEvalRequest(BaseModel):
    example_id: str
    actual_output: str
    tools_used: list[str] = Field(default_factory=list)


class LogIncidentRequest(BaseModel):
    organization_id: uuid.UUID
    run_id: uuid.UUID | None = None
    severity: IncidentSeverity
    category: str
    title: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecordReplayRequest(BaseModel):
    organization_id: uuid.UUID
    run_id: uuid.UUID
    request: str
    model: str
    final_response: str | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/safety", response_model=SafetyScore)
async def evaluate_safety(req: EvaluateSafetyRequest, current_user: CurrentUserDep) -> SafetyScore:
    if current_user.organization_id != req.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Compute safety score for an agent run."""
    return SafetyEvaluator.evaluate(
        run_id=req.run_id,
        organization_id=req.organization_id,
        action_history=[],
        policy_violations=req.policy_violations,
        unauthorized_tool_attempts=req.unauthorized_tool_attempts,
        prompt_injection_attempts=req.prompt_injection_attempts,
        tenant_boundary_violations=req.tenant_boundary_violations,
        failed_verifications=req.failed_verifications,
    )


@router.post("/quality", response_model=QualityScore)
async def evaluate_quality(req: EvaluateQualityRequest, current_user: CurrentUserDep) -> QualityScore:
    if current_user.organization_id != req.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Compute quality score for an agent run."""
    return QualityEvaluator.evaluate(
        run_id=req.run_id,
        organization_id=req.organization_id,
        succeeded=req.succeeded,
        action_history=[],
        expected_tools=req.expected_tools,
        actual_tools_used=req.actual_tools_used,
        retrieved_chunks=req.retrieved_chunks,
        cited_chunks=req.cited_chunks,
        policy_compliant=req.policy_compliant,
        latency_ms=req.latency_ms,
        estimated_cost_usd=req.estimated_cost_usd,
    )


@router.post("/cost")
async def estimate_cost(req: CostEstimateRequest, current_user: CurrentUserDep) -> dict[str, Any]:
    if current_user.organization_id != req.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Estimate and check budget for a model invocation."""
    estimate = CostManager.estimate_cost(
        model=req.model,
        provider=req.provider,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
    )
    budget = CostManager.check_budget(
        organization_id=req.organization_id,
        estimated_cost_usd=estimate.estimated_cost_usd,
        run_id=req.run_id,
        per_run_budget_usd=req.per_run_budget_usd,
    )
    if budget.status == BudgetStatus.EXCEEDED:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=budget.message,
        )
    return {
        "estimate": estimate.model_dump(),
        "budget": budget.model_dump(),
    }


@router.get("/benchmarks")
async def get_benchmarks(current_user: CurrentUserDep, db: DatabaseDep, task_type: str | None = None) -> dict[str, Any]:
    # Query actual eval runs
    query = select(EvalRun).where(EvalRun.organization_id == current_user.organization_id)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    benchmarks = []
    for r in runs:
        benchmarks.append({
            "model": r.model,
            "provider": r.provider,
            "task_type": "GENERAL",
            "success_rate": r.success_rate,
            "avg_latency_ms": r.avg_latency_ms,
            "avg_tokens": r.avg_tokens,
            "avg_cost_usd": r.avg_cost_usd,
            "sample_count": r.sample_count,
        })
        
    return {
        "benchmarks": benchmarks,
        "recommendation": None
    }


@router.get("/datasets")
async def get_datasets(current_user: CurrentUserDep, db: DatabaseDep, category: str | None = None) -> dict[str, Any]:
    query = select(EvalDataset).where(EvalDataset.organization_id == current_user.organization_id)
    if category:
        query = query.where(EvalDataset.category == category)
    
    result = await db.execute(query)
    datasets = result.scalars().all()
    
    if not datasets:
        # Seed lazily from ALL_GOLDEN_EXAMPLES
        from app.evaluation.datasets import ALL_GOLDEN_EXAMPLES
        grouped = {}
        for ex in ALL_GOLDEN_EXAMPLES:
            if ex.category not in grouped:
                grouped[ex.category] = []
            grouped[ex.category].append(ex)
            
        for cat, examples in grouped.items():
            ds = EvalDataset(
                organization_id=current_user.organization_id,
                name=f"{cat.title()} Golden Dataset",
                description=f"Standard golden examples for {cat} tasks.",
                category=cat,
                version=1
            )
            db.add(ds)
            await db.flush()
            for ex in examples:
                db_ex = EvalExample(
                    dataset_id=ds.id,
                    input_prompt=ex.input.replace('\x00', '\\x00'),
                    expected_tools=ex.expected_tools,
                    expected_output_contains=ex.expected_output_contains,
                    must_not_contain=ex.must_not_contain,
                    is_attack=ex.is_attack,
                    attack_type=ex.attack_type
                )
                db.add(db_ex)
        await db.commit()
        
        result = await db.execute(query)
        datasets = result.scalars().all()
        
    ds_list = []
    for ds in datasets:
        ds_list.append({
            "id": str(ds.id),
            "name": ds.name,
            "description": ds.description,
            "category": ds.category,
            "version": ds.version
        })
        
    return {
        "count": len(ds_list),
        "examples": ds_list,
        "attacks": 0
    }


@router.post("/datasets/evaluate")
async def evaluate_against_golden(req: GoldenEvalRequest, current_user: CurrentUserDep) -> dict[str, Any]:
    """Evaluate an agent output against a golden example."""
    example = next((e for e in ALL_GOLDEN_EXAMPLES if e.id == req.example_id), None)
    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden example '{req.example_id}' not found.",
        )
    result = GoldenDatasetEvaluator.evaluate_example(
        example=example,
        actual_output=req.actual_output,
        tools_used=req.tools_used,
    )
    return result


@router.post("/incidents")
async def log_incident(req: LogIncidentRequest, current_user: CurrentUserDep) -> dict[str, Any]:
    if current_user.organization_id != req.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Log an incident record."""
    incident = IncidentLogger.log(
        organization_id=req.organization_id,
        run_id=req.run_id,
        severity=req.severity,
        category=req.category,
        title=req.title,
        description=req.description,
        metadata=req.metadata,
    )
    return {"id": incident.id, "logged": True}


@router.get("/incidents/{organization_id}")
async def get_incidents(organization_id: uuid.UUID, current_user: CurrentUserDep, limit: int = 50) -> dict[str, Any]:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail='Access denied')
    """Get tenant-isolated incident log."""
    incidents = IncidentLogger.get_org_incidents(organization_id, limit=limit)
    return {
        "organization_id": str(organization_id),
        "count": len(incidents),
        "incidents": [i.model_dump() for i in incidents],
    }


@router.post("/replay/record")
async def record_replay(req: RecordReplayRequest, current_user: CurrentUserDep) -> dict[str, Any]:
    if current_user.organization_id != req.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    """Record a run for potential replay."""
    ReplayEngine.record(
        organization_id=req.organization_id,
        run_id=req.run_id,
        request=req.request,
        model=req.model,
        final_response=req.final_response,
    )
    return {"run_id": str(req.run_id), "recorded": True}


@router.get("/replay/{organization_id}/{run_id}")
async def get_replay(organization_id: uuid.UUID, current_user: CurrentUserDep, run_id: uuid.UUID) -> dict[str, Any]:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail='Access denied')
    """Retrieve a recorded run for replay — tenant isolated."""
    record = ReplayEngine.get(organization_id, run_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Replay record not found or access denied.",
        )
    return record


@router.get("/replay/{organization_id}/{run_id}/export")
async def export_replay(organization_id: uuid.UUID, current_user: CurrentUserDep, run_id: uuid.UUID) -> dict[str, Any]:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail='Access denied')
    """Export a run trace as JSON — tenant isolated."""
    json_str = ReplayEngine.export_json(organization_id, run_id)
    if not json_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found or access denied.",
        )
    return {"run_id": str(run_id), "format": "json", "data": json_str}


@router.get("/ops/{organization_id}")
async def get_ops_metrics(organization_id: uuid.UUID, current_user: CurrentUserDep, window_hours: int = 24) -> dict[str, Any]:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail='Access denied')
    """
    Get AI Operations dashboard metrics for an organization.
    Returns a mock/empty metrics object when DB is not available.
    Always tenant-isolated.
    """
    metrics = OpsMetrics(
        organization_id=organization_id,
        window_hours=window_hours,
    )
    return metrics.model_dump()


@router.get("/org/{organization_id}/spend")
async def get_org_spend(organization_id: uuid.UUID, current_user: CurrentUserDep) -> dict[str, Any]:
    if current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail='Access denied')
    """Get current daily spend for an organization."""
    spend = CostManager.get_org_daily_spend(organization_id)
    return {
        "organization_id": str(organization_id),
        "daily_spend_usd": spend,
        "daily_budget_usd": 50.0,
        "remaining_usd": max(0.0, 50.0 - spend),
    }


from fastapi import BackgroundTasks
from pydantic import BaseModel

class RunEvalRequest(BaseModel):
    dataset_id: uuid.UUID
    provider: str
    model: str

async def execute_eval_run_background(eval_run_id: uuid.UUID, user_id: uuid.UUID):
    import asyncio, time, traceback
    from datetime import datetime, timezone
    import sqlalchemy as sa
    import structlog
    from app.ai.services.llm import LLMService
    from app.agents.services.agent_service import AgentWorkflowService
    from app.database.base import get_session_factory
    from app.database.models import (
        AgentRun, AgentRunStatus, AgentTraceEvent, Conversation, ConversationStatus,
        EvalExample, EvalResult, EvalRun, Message, MessageRole,
    )
    from app.knowledge.rag_service import RAGService

    logger = structlog.get_logger(__name__)
    factory = get_session_factory()
    passed_count, total_latency, persistence_failed = 0, 0.0, False
    try:
        async with factory() as db:
            run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
            if run is None:
                return
            run.status = "running"
            await db.commit()
            examples = list((await db.scalars(sa.select(EvalExample).where(
                EvalExample.dataset_id == run.dataset_id
            ))).all())
            org_id, provider = run.organization_id, run.provider

        for example in examples:
            started = time.monotonic()
            output, tools, error, passed = None, [], None, False
            latency = 0
            try:
                async with factory() as session:
                    try:
                        llm = LLMService()
                        if provider == "mock":
                            from app.ai.providers.mock import MockLLMProvider
                            llm.provider = MockLLMProvider()
                        service = AgentWorkflowService(session, llm, RAGService(session, llm))
                        conv = Conversation(organization_id=org_id, user_id=user_id,
                            title=f"Eval {eval_run_id} Ex {example.id}", status=ConversationStatus.ACTIVE)
                        session.add(conv); await session.flush()
                        agent_run = AgentRun(conversation_id=conv.id, user_id=user_id,
                            user_request=example.input_prompt, status=AgentRunStatus.PENDING)
                        session.add(agent_run); await session.flush()
                        session.add(Message(conversation_id=conv.id, role=MessageRole.USER,
                            content=example.input_prompt, agent_run_id=agent_run.id))
                        await session.commit()
                        try:
                            await asyncio.wait_for(service.execute_run(agent_run.id), timeout=60.0)
                        except Exception as exc:
                            error = f"{type(exc).__name__}: {exc}"
                        await session.rollback()
                        stored = await session.scalar(sa.select(AgentRun).where(AgentRun.id == agent_run.id))
                        if stored:
                            output = stored.final_response
                            if not output and stored.error_message and not error:
                                error = stored.error_message
                        traces = await session.scalars(sa.select(AgentTraceEvent).where(
                            AgentTraceEvent.run_id == agent_run.id))
                        tools = [t.metadata_["tool"] for t in traces.all()
                            if t.event_type == "tool_execution" and t.metadata_ and "tool" in t.metadata_]
                        if output:
                            lower = output.lower()
                            missing = next((x for x in (example.expected_output_contains or []) if x.lower() not in lower), None)
                            forbidden = next((x for x in (example.must_not_contain or []) if x.lower() in lower), None)
                            missing_tool = next((x for x in (example.expected_tools or []) if x not in tools), None)
                            if missing: error = f"Missing expected content: {missing}"
                            elif forbidden: error = f"Contained forbidden content: {forbidden}"
                            elif missing_tool: error = f"Missing expected tool: {missing_tool}"
                            else: passed = error is None
                        elif not error:
                            error = "No output produced"
                    except Exception as exc:
                        await session.rollback()
                        error = f"{type(exc).__name__}: {exc}"
                        output, tools, passed = None, [], False

                    latency = int((time.monotonic() - started) * 1000)
                    total_latency += latency
                    session.add(EvalResult(run_id=eval_run_id, example_id=example.id,
                        actual_output=output, tools_used=tools, passed=passed, error_message=error,
                        latency_ms=latency, total_tokens=0, cost_usd=0.0))
                    await session.commit()
                    if passed: passed_count += 1
            except Exception as exc:
                latency = int((time.monotonic() - started) * 1000)
                total_latency += latency
                error = f"Could not execute or persist example: {type(exc).__name__}: {exc}"
                logger.error("eval_example_error", run_id=str(eval_run_id),
                    example_id=str(example.id), error=error, trace=traceback.format_exc())
                try:
                    async with factory() as failed:
                        failed.add(EvalResult(run_id=eval_run_id, example_id=example.id,
                            actual_output=None, tools_used=[], passed=False, error_message=error,
                            latency_ms=latency, total_tokens=0, cost_usd=0.0))
                        await failed.commit()
                except Exception:
                    persistence_failed = True
                    logger.exception("eval_failure_result_persist_failed", run_id=str(eval_run_id))

        async with factory() as db:
            run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
            if run:
                count = await db.scalar(sa.select(sa.func.count(EvalResult.id)).where(
                    EvalResult.run_id == eval_run_id))
                run.success_rate = passed_count / len(examples) if examples else 0.0
                run.avg_latency_ms = total_latency / len(examples) if examples else 0.0
                run.sample_count = len(examples)
                run.completed_at = datetime.now(timezone.utc)
                run.status = "failed" if persistence_failed or (count or 0) != len(examples) else "completed"
                await db.commit()
    except Exception:
        logger.exception("eval_run_failed", run_id=str(eval_run_id))
        try:
            async with factory() as db:
                run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            logger.exception("eval_run_status_persist_failed", run_id=str(eval_run_id))


@router.post("/runs")
async def run_evaluation(req: RunEvalRequest, current_user: CurrentUserDep, db: DatabaseDep, background_tasks: BackgroundTasks) -> dict[str, Any]:
    # Ensure dataset exists
    ds = await db.scalar(select(EvalDataset).where(EvalDataset.id == req.dataset_id, EvalDataset.organization_id == current_user.organization_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    eval_run = EvalRun(
        organization_id=current_user.organization_id,
        dataset_id=ds.id,
        model=req.model,
        provider=req.provider,
        status="pending",
    )
    db.add(eval_run)
    await db.commit()
    
    background_tasks.add_task(execute_eval_run_background, eval_run.id, current_user.id)
    return {"run_id": str(eval_run.id), "status": "pending"}

@router.get("/runs")
async def get_eval_runs(current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    query = select(EvalRun).where(EvalRun.organization_id == current_user.organization_id).order_by(EvalRun.completed_at.desc()).limit(20)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    out = []
    for r in runs:
        out.append({
            "id": str(r.id),
            "dataset_id": str(r.dataset_id),
            "model": r.model,
            "provider": r.provider,
            "status": r.status,
            "success_rate": r.success_rate,
            "avg_latency_ms": r.avg_latency_ms,
            "sample_count": r.sample_count,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None
        })
    return {"runs": out}

@router.get("/runs/{run_id}")
async def get_eval_run_details(run_id: uuid.UUID, current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    run = await db.scalar(select(EvalRun).where(EvalRun.id == run_id, EvalRun.organization_id == current_user.organization_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    res_query = select(EvalResult, EvalExample).join(EvalExample, EvalResult.example_id == EvalExample.id).where(EvalResult.run_id == run.id)
    res_result = await db.execute(res_query)
    results_and_examples = res_result.all()
    
    return {
        "run": {
            "id": str(run.id),
            "model": run.model,
            "status": run.status,
            "success_rate": run.success_rate,
            "sample_count": run.sample_count,
            "avg_latency_ms": run.avg_latency_ms,
            "expected_count": await db.scalar(select(func.count(EvalExample.id)).where(EvalExample.dataset_id == run.dataset_id)),
        },
        "results": [
            {
                "example_id": str(res.id),
                "input_prompt": ex.input_prompt,
                "expected_tools": ex.expected_tools,
                "actual_output": res.actual_output,
                "passed": res.passed,
                "tools_used": res.tools_used,
                "error_message": res.error_message,
                "latency_ms": res.latency_ms
            } for res, ex in results_and_examples
        ]
    }

@router.get("/datasets/{dataset_id}")
async def get_dataset_details(dataset_id: uuid.UUID, current_user: CurrentUserDep, db: DatabaseDep) -> dict[str, Any]:
    ds = await db.scalar(select(EvalDataset).where(EvalDataset.id == dataset_id, EvalDataset.organization_id == current_user.organization_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    examples = await db.scalars(select(EvalExample).where(EvalExample.dataset_id == ds.id))
    ex_list = [
        {
            "id": str(ex.id),
            "input_prompt": ex.input_prompt,
            "expected_tools": ex.expected_tools,
            "expected_output_contains": ex.expected_output_contains,
            "must_not_contain": ex.must_not_contain,
            "is_attack": ex.is_attack
        } for ex in examples.all()
    ]
    
    return {
        "dataset": {
            "id": str(ds.id),
            "name": ds.name,
            "description": ds.description,
            "category": ds.category
        },
        "examples": ex_list
    }
