import re
import os

path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

eval_runs_code = """
from fastapi import BackgroundTasks
from pydantic import BaseModel

class RunEvalRequest(BaseModel):
    dataset_id: str
    provider: str
    model: str

async def execute_eval_run_background(eval_run_id: uuid.UUID, user_id: uuid.UUID):
    import time
    from app.database.base import get_session_factory
    from app.ai.services.llm import LLMService
    from app.knowledge.rag_service import RAGService
    from app.agents.services.agent_service import AgentWorkflowService
    from app.database.models import Conversation, ConversationStatus, AgentRun, AgentRunStatus, Message, MessageRole, EvalRun, EvalResult, EvalExample
    import asyncio
    import sqlalchemy as sa
    
    SessionFactory = get_session_factory()
    async with SessionFactory() as db:
        # Load EvalRun
        eval_run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
        if not eval_run:
            return
            
        examples = await db.scalars(sa.select(EvalExample).where(EvalExample.dataset_id == eval_run.dataset_id))
        examples = examples.all()
        
        llm = LLMService()
        rag = RAGService(db, llm)
        agent_service = AgentWorkflowService(db, llm, rag)
        
        total_examples = len(examples)
        passed = 0
        total_latency = 0.0
        total_tokens = 0.0
        
        for ex in examples:
            start_t = time.time()
            conv = Conversation(
                organization_id=eval_run.organization_id,
                user_id=user_id,
                title=f"Eval {eval_run.id} Ex {ex.id}",
                status=ConversationStatus.ACTIVE
            )
            db.add(conv)
            await db.flush()
            
            agent_run = AgentRun(
                conversation_id=conv.id,
                user_id=user_id,
                status=AgentRunStatus.PENDING
            )
            db.add(agent_run)
            await db.flush()
            
            msg = Message(
                conversation_id=conv.id, 
                role=MessageRole.USER, 
                content=ex.input_prompt, 
                agent_run_id=agent_run.id
            )
            db.add(msg)
            await db.commit()
            
            # Execute real pipeline
            actual_output = None
            tools_used = []
            error_msg = None
            try:
                state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0)
                agent_run = await db.scalar(sa.select(AgentRun).where(AgentRun.id == agent_run.id))
                actual_output = agent_run.final_result or agent_run.error_message
                
                # Extract tools used from trace
                from app.database.models import AgentTraceEvent
                traces = await db.scalars(sa.select(AgentTraceEvent).where(AgentTraceEvent.run_id == agent_run.id))
                for t in traces.all():
                    if t.event_type == "tool_execution":
                        if t.metadata_ and "tool" in t.metadata_:
                            tools_used.append(t.metadata_["tool"])
            except Exception as e:
                error_msg = str(e)
                actual_output = "Error during execution."
                
            latency = (time.time() - start_t) * 1000
            total_latency += latency
            
            # Evaluate pass/fail logic
            is_pass = True
            if actual_output:
                act_lower = actual_output.lower()
                for c in (ex.expected_output_contains or []):
                    if c.lower() not in act_lower:
                        is_pass = False
                        error_msg = f"Missing expected content: {c}"
                for c in (ex.must_not_contain or []):
                    if c.lower() in act_lower:
                        is_pass = False
                        error_msg = f"Contained forbidden content: {c}"
                        
                # strict tool check
                for t in (ex.expected_tools or []):
                    if t not in tools_used:
                        is_pass = False
                        error_msg = f"Missing expected tool: {t}"
            else:
                is_pass = False
                error_msg = "No output produced"
                
            if is_pass:
                passed += 1
                
            res = EvalResult(
                run_id=eval_run.id,
                example_id=ex.id,
                actual_output=actual_output,
                tools_used=tools_used,
                passed=is_pass,
                error_message=error_msg,
                latency_ms=int(latency),
                total_tokens=int(agent_run.total_tokens_output or 0) if agent_run else 0,
                cost_usd=0.0 # TODO CostManager
            )
            db.add(res)
            
            if agent_run:
                total_tokens += (agent_run.total_tokens_output or 0)
                
        # Finalize run
        eval_run.success_rate = (passed / total_examples) if total_examples else 0.0
        eval_run.avg_latency_ms = (total_latency / total_examples) if total_examples else 0.0
        eval_run.avg_tokens = (total_tokens / total_examples) if total_examples else 0.0
        eval_run.sample_count = total_examples
        
        await db.commit()

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
        provider=req.provider
    )
    db.add(eval_run)
    await db.commit()
    
    background_tasks.add_task(execute_eval_run_background, eval_run.id, current_user.id)
    return {"run_id": str(eval_run.id), "status": "running"}

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
        
    res_query = select(EvalResult).where(EvalResult.run_id == run.id)
    res_result = await db.execute(res_query)
    results = res_result.scalars().all()
    
    return {
        "run": {
            "id": str(run.id),
            "model": run.model,
            "success_rate": run.success_rate,
            "sample_count": run.sample_count,
            "avg_latency_ms": run.avg_latency_ms
        },
        "results": [
            {
                "example_id": str(res.example_id),
                "actual_output": res.actual_output,
                "passed": res.passed,
                "tools_used": res.tools_used,
                "error_message": res.error_message,
                "latency_ms": res.latency_ms
            } for res in results
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
"""

if "class RunEvalRequest" not in text:
    text += "\n" + eval_runs_code
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched eval.py")
else:
    print("Already patched.")
