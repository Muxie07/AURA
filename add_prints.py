import re
path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('start_t = time.time()', 'start_t = time.time()\n                print("Loop start")')
text = text.replace('db.add(conv)', 'db.add(conv)\n                    print("Added conv")')
text = text.replace('await db.flush()', 'await db.flush()\n                    print("Flushed")')
text = text.replace('db.add(agent_run)', 'db.add(agent_run)\n                    print("Added agent run")')
text = text.replace('db.add(msg)', 'db.add(msg)\n                    print("Added msg")')
text = text.replace('state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0)', 'print("Executing agent"); state = await asyncio.wait_for(agent_service.execute_run(agent_run.id), timeout=60.0); print("Agent done")')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
