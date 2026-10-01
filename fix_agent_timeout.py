import os

agent_path = r'backend/app/api/v1/agent.py'
with open(agent_path, 'r') as f:
    agent_code = f.read()

old_bg_run = '''        try:
            await agent_service.execute_run(run_id)
        except BaseException:
            traceback.print_exc()'''

new_bg_run = '''        try:
            import asyncio
            await asyncio.wait_for(agent_service.execute_run(run_id), timeout=300.0)
        except asyncio.TimeoutError:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.error("agent_run_timeout", run_id=str(run_id))
        except BaseException:
            traceback.print_exc()'''

if old_bg_run in agent_code:
    agent_code = agent_code.replace(old_bg_run, new_bg_run)
else:
    print('old_bg_run not found')

with open(agent_path, 'w') as f:
    f.write(agent_code)

print('Done patching agent.py for timeout.')
