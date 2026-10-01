import re
path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# I will replace the background task once more, making it perfectly robust.
new_func = """async def execute_eval_run_background(eval_run_id: uuid.UUID, user_id: uuid.UUID):
    import time, traceback
    from app.database.base import get_session_factory
    from app.ai.services.llm import LLMService
    from app.knowledge.rag_service import RAGService
    from app.agents.services.agent_service import AgentWorkflowService
    from app.database.models import Conversation, ConversationStatus, AgentRun, AgentRunStatus, Message, MessageRole, EvalRun, EvalResult, EvalExample
    import asyncio
    import sqlalchemy as sa
    from datetime import datetime, timezone
    
    SessionFactory = get_session_factory()
    
    async with SessionFactory() as db:
        eval_run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
        if not eval_run:
            return
        examples = await db.scalars(sa.select(EvalExample).where(EvalExample.dataset_id == eval_run.dataset_id))
        examples = examples.all()
        dataset_id = eval_run.dataset_id
        org_id = eval_run.organization_id
        
    total_examples = len(examples)
    passed = 0
    total_latency = 0.0
    
    for ex in examples:
        start_t = time.time()
        async with SessionFactory() as session:
            try:
                llm = LLMService()
                if eval_run.provider != "mock":
                    # For eval override
                    pass # We just use the default configured provider for real tests
                else:
                    from app.ai.providers.mock import MockLLMProvider
                    llm.provider = MockLLMProvider()
                    
                rag = RAGService(session, llm)
                agent_service = AgentWorkflowService(session, llm, rag)
                
                conv = Conversation(
                    organization_id=org_id,
                    user_id=user_id,
                    title=f"Eval {eval_run_id} Ex {ex.id}",
                    status=ConversationStatus.ACTIVE
                )
                session.add(conv)
                await session.flush()
                
                agent_run = AgentRun(
                    conversation_id=conv.id,
                    user_id=user_id,
                    user_request=ex.input_prompt,
                    status=AgentRunStatus.PENDING
                )
                session.add(agent_run)
                await session.flush()
                
                msg = Message(
                    conversation_id=conv.id, 
                    role=MessageRole.USER, 
                    content=ex.input_prompt, 
                    agent_run_id=agent_run.id
                )
                session.add(msg)
                await session.commit()
                
                actual_output = None
                tools_used = []
                error_msg = None
                
                try:
                    state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0)
                except asyncio.TimeoutError:
                    error_msg = "Timeout after 60s"
                except Exception as e:
                    error_msg = str(e)
                    
                # We start a new transaction just to read results in case the previous one errored out
                await session.rollback()
                
                agent_run_db = await session.scalar(sa.select(AgentRun).where(AgentRun.id == agent_run.id))
                if agent_run_db:
                    actual_output = agent_run_db.final_result or agent_run_db.error_message
                    
                from app.database.models import AgentTraceEvent
                traces = await session.scalars(sa.select(AgentTraceEvent).where(AgentTraceEvent.run_id == agent_run.id))
                for t in traces.all():
                    if t.event_type == "tool_execution" and t.metadata_ and "tool" in t.metadata_:
                        tools_used.append(t.metadata_["tool"])
                        
                latency = (time.time() - start_t) * 1000
                total_latency += latency
                
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
                    for t in (ex.expected_tools or []):
                        if t not in tools_used:
                            is_pass = False
                            error_msg = f"Missing expected tool: {t}"
                else:
                    is_pass = False
                    if not error_msg: error_msg = "No output produced"
                    
                if is_pass:
                    passed += 1
                    
                res = EvalResult(
                    run_id=eval_run_id,
                    example_id=ex.id,
                    actual_output=actual_output,
                    tools_used=tools_used,
                    passed=is_pass,
                    error_message=error_msg,
                    latency_ms=int(latency),
                    total_tokens=0,
                    cost_usd=0.0
                )
                session.add(res)
                await session.commit()
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("eval_example_error", error=str(e), trace=traceback.format_exc())

    async with SessionFactory() as db:
        try:
            eval_run = await db.scalar(sa.select(EvalRun).where(EvalRun.id == eval_run_id))
            if eval_run:
                eval_run.success_rate = (passed / total_examples) if total_examples else 0.0
                eval_run.avg_latency_ms = (total_latency / total_examples) if total_examples else 0.0
                eval_run.sample_count = total_examples
                eval_run.completed_at = datetime.now(timezone.utc)
                await db.commit()
        except:
            pass
"""

text = re.sub(r'async def execute_eval_run_background.*?@router\.post\("/runs"\)', new_func + '\n@router.post("/runs")', text, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Replaced background run")
