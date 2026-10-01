path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('actual_output = agent_run_db.final_result or agent_run_db.error_message', 'actual_output = agent_run_db.final_response or agent_run_db.error_message')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed final_response attr")
