import re
import json

tool_output = {"customers": [{"id": "CUST-001", "name": "Acme Technologies", "email": "contact@acme.com"}]}
context = f"Tool result: {json.dumps(tool_output)}"
user_prompt_dec = context.lower()

match = re.search(r'"id":\s*"([^"]+)"', user_prompt_dec)
print("Matched ID:", match.group(1) if match else "None")
