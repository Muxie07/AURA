path = "backend/app/ai/providers/heuristic.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

import re
text = text.replace(
    r"ready_steps = re.findall(r'- id:\s*([^,]+),\s*type:\s*([^\n]+)', sys_prompt)",
    r"""ready_steps = []
            for action in ['customer.search', 'quotation.create_draft', 'observability.get_api_latency', 'product.search', 'pricing.calculate']:
                if f"type: {action}" in sys_prompt or f"type: {action}" in sys_prompt:
                    match = re.search(r'- id:\s*([^,]+),\s*type:\s*' + action, sys_prompt)
                    if match:
                        ready_steps.append((match.group(1), action))"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed regex in heuristic.py")
