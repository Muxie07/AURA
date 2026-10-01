with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

routes_addition = '''
@router.get("/agent/runs")
async def list_agent_runs(db: DatabaseDep) -> Any:
    runs = await db.scalars(
        sa.select(AgentRun).order_by(AgentRun.started_at.desc())
    )
    return {"runs": [
        {
            "run_id": str(r.id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "final_result": r.final_response,
            "error_message": r.error_message
        } for r in runs
    ]}
'''

text = text + routes_addition

with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)
