with open("backend/app/agents/execution/decision.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'await redis_client.publish(f"run_stream_' in line and 'event_type' in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + "data_str = '{\"event_type\": \"content_delta\", \"content\": \"' + msg + '\"}'\n")
        new_lines.append(indent + 'await redis_client.publish(f"run_stream_{state.run_id}", f"data: {data_str}\\n\\n")\n')
    else:
        new_lines.append(line)

with open("backend/app/agents/execution/decision.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
