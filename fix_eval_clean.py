import re
path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('db.add(conv)\n                    print("Added conv")', 'db.add(conv)')
text = text.replace('await db.flush()\n                    print("Flushed")', 'await db.flush()')
text = text.replace('db.add(agent_run)\n                    print("Added agent run")', 'db.add(agent_run)')
text = text.replace('db.add(msg)\n                    print("Added msg")', 'db.add(msg)')
text = text.replace('print("Executing agent"); state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0); print("Agent done")', 'state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0)')
text = text.replace('start_t = time.time()\n                print("Loop start")', 'start_t = time.time()')

# Now fix the missing user_request
text = text.replace('agent_run = AgentRun(\n                        conversation_id=conv.id,\n                        user_id=user_id,\n                        status=AgentRunStatus.PENDING\n                    )', 'agent_run = AgentRun(\n                        conversation_id=conv.id,\n                        user_id=user_id,\n                        user_request=ex.input_prompt,\n                        status=AgentRunStatus.PENDING\n                    )')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed eval.py")
