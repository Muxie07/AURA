import io

with io.open("backend/app/api/v1/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

stream_code = """
import json
import asyncio
from fastapi.responses import StreamingResponse

@router.get("/agent/runs/{run_id}/stream")
async def stream_agent_trace(run_id: uuid.UUID, db: DatabaseDep, current_user: CurrentUserDep):
    run = await db.scalar(
        sa.select(AgentRun).join(Conversation).where(
            AgentRun.id == run_id,
            Conversation.organization_id == current_user.organization_id
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        last_sequence = -1
        # Loop until run completes
        while True:
            # Re-fetch run status to know if we should stop
            await db.refresh(run)
            events = await db.scalars(
                sa.select(AgentTraceEvent).where(
                    AgentTraceEvent.run_id == run_id,
                    AgentTraceEvent.sequence > last_sequence
                ).order_by(AgentTraceEvent.sequence)
            )
            for event in events:
                data = {
                    "id": str(event.id),
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "component": event.component,
                    "timestamp": event.timestamp.isoformat(),
                    "duration_ms": event.duration_ms,
                    "metadata": event.metadata_
                }
                yield f"data: {json.dumps(data)}\\n\\n"
                last_sequence = event.sequence
            
            if run.status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):
                # Send one final event to close
                yield f"data: {json.dumps({'event_type': 'STREAM_END', 'status': run.status})}\\n\\n"
                break
                
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
"""

content = content.replace("from fastapi import APIRouter, BackgroundTasks", "from fastapi import APIRouter, BackgroundTasks\nfrom fastapi.responses import StreamingResponse\nimport json\nimport asyncio")
content += "\n" + stream_code

with io.open("backend/app/api/v1/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
