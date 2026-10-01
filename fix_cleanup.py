import sys
with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

lines = text.split('\n')
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if 'agent_service = AgentWorkflowService' in line:
        start_idx = i
    if 'summary={"plan"' in line:
        end_idx = i + 2
        break

replacement = """    agent_service = AgentWorkflowService(db, llm, rag)
    try:
        await agent_service.execute_run(run.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await agent_service.aclose()

    await db.refresh(run)

    return AgentRunResponse(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        final_result=run.final_response,
        error_message=run.error_message,
        summary={"plan": run.plan, "iterations": run.iteration_count}
    )
"""
new_lines = lines[:start_idx] + replacement.split('\n') + lines[end_idx:]
with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write('\n'.join(new_lines))
