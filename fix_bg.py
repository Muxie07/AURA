with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

replacement = \"\"\"
        try:
            import asyncio
            await asyncio.wait_for(agent_service.execute_run(run_id), timeout=300.0)
        except asyncio.TimeoutError:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.error("agent_run_timeout", run_id=str(run_id))
            run = await db.scalar(sa.select(AgentRun).where(AgentRun.id == run_id))
            if run:
                run.status = AgentRunStatus.FAILED
                run.error_message = "Agent execution timed out."
                await db.commit()
        except BaseException as e:
            traceback.print_exc()
            run = await db.scalar(sa.select(AgentRun).where(AgentRun.id == run_id))
            if run:
                run.status = AgentRunStatus.FAILED
                run.error_message = f"Agent execution failed: {str(e) or 'Unknown error'}"
                await db.commit()
        finally:
\"\"\"

import re
text = re.sub(r'        try:\n            import asyncio.*?        finally:', replacement.strip('\n'), text, flags=re.DOTALL)

with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)
