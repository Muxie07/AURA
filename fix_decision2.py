with open("backend/app/agents/execution/decision.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_dec = """
                await redis_client.publish(f"run_stream_{state.run_id}", f"data: {{\\"event_type\\": \\"content_delta\\", \\"content\\": \\"{msg}\\"}}\\n\\n")
"""

new_dec = """
                data = '{"event_type": "content_delta", "content": "' + msg + '"}'
                await redis_client.publish(f"run_stream_{state.run_id}", f"data: {data}\\n\\n")
"""

text = text.replace(old_dec.strip(), new_dec.strip())

with open("backend/app/agents/execution/decision.py", "w", encoding="utf-8") as f:
    f.write(text)
