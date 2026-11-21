import re
path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('async def execute_eval_run_background(eval_run_id: uuid.UUID, user_id: uuid.UUID):', 'async def execute_eval_run_background(eval_run_id: uuid.UUID, user_id: uuid.UUID):\n    print(f"BACKGROUND TASK STARTED FOR RUN {eval_run_id}")\n')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
