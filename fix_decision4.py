with open("backend/app/agents/execution/decision.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_dec = """
        if not state.plan or not state.plan.steps:
            # Check if this is our latency check
            if state.plan and state.plan.goal and "latency" in state.plan.goal.lower():
                msg = "I can investigate API latency, but no latency/observability data source is currently connected to AURA."
                state.final_response = msg
                import redis.asyncio as aioredis
                from app.config.settings import get_settings
                settings = get_settings()
                redis_client = aioredis.from_url(settings.redis_url)
                data_str = '{"event_type": "content_delta", "content": "' + msg + '"}'
                await redis_client.publish(f"run_stream_{state.run_id}", f"data: {data_str}\\n\\n")
                await redis_client.aclose()
                state.status = AgentNodeState.COMPLETED
                return state

            # Generate direct response without steps
"""

new_dec = """
        if not state.plan or not state.plan.steps:
            # Generate direct response without steps
"""

text = text.replace(old_dec.strip(), new_dec.strip())

with open("backend/app/agents/execution/decision.py", "w", encoding="utf-8") as f:
    f.write(text)
