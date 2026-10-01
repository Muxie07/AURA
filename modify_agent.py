with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

from_addition = '''from app.database.models import AgentTraceEvent, ApprovalRequest, ApprovalStatus
'''

routes_addition = '''
@router.get("/agent/runs/{run_id}/trace")
async def get_agent_trace(run_id: uuid.UUID, db: DatabaseDep) -> Any:
    events = await db.scalars(
        sa.select(AgentTraceEvent).where(AgentTraceEvent.run_id == run_id).order_by(AgentTraceEvent.sequence)
    )
    return {"events": [
        {
            "id": str(e.id),
            "sequence": e.sequence,
            "event_type": e.event_type,
            "component": e.component,
            "timestamp": e.timestamp.isoformat(),
            "duration_ms": e.duration_ms,
            "metadata": e.metadata_
        } for e in events
    ]}

@router.get("/agent/approvals")
async def list_approvals(db: DatabaseDep) -> Any:
    approvals = await db.scalars(
        sa.select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    )
    return {"approvals": [
        {
            "id": str(a.id),
            "run_id": str(a.run_id),
            "tool_name": a.tool_name,
            "risk_level": a.risk_level,
            "status": a.status,
            "created_at": a.created_at.isoformat()
        } for a in approvals
    ]}

@router.post("/agent/approvals/{approval_id}/approve")
async def approve_request(approval_id: uuid.UUID, db: DatabaseDep) -> Any:
    approval = await db.scalar(sa.select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = ApprovalStatus.APPROVED
    await db.commit()
    return {"status": "APPROVED"}

@router.post("/agent/approvals/{approval_id}/reject")
async def reject_request(approval_id: uuid.UUID, db: DatabaseDep) -> Any:
    approval = await db.scalar(sa.select(ApprovalRequest).where(ApprovalRequest.id == approval_id))
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = ApprovalStatus.DENIED
    await db.commit()
    return {"status": "DENIED"}
'''

text = from_addition + text + routes_addition

with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)
