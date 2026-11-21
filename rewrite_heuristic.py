import re

with open("backend/app/ai/providers/heuristic.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update the planner to emit two steps for quotation
planner_replacement = """        if schema.__name__ == "StructuredAgentPlan":
            # Heuristic planner logic
            if "quotation" in user_prompt:
                data = {
                    "goal": "Create a draft quotation",
                    "steps": [
                        {
                            "id": "step_1",
                            "type": "customer.search",
                            "description": "Search for customer",
                            "dependencies": [],
                            "required_tools": ["customer.search"],
                            "risk": "LOW",
                            "expected_output": "Customer details",
                            "verification_criteria": "None",
                            "status": "pending"
                        },
                        {
                            "id": "step_2",
                            "type": "quotation.create_draft",
                            "description": "Create a new quotation draft",
                            "dependencies": ["step_1"],
                            "required_tools": ["quotation.create_draft"],
                            "risk": "HIGH",
                            "expected_output": "Quotation created successfully",
                            "verification_criteria": "None",
                            "status": "pending"
                        }
                    ]
                }"""

# Replace the old planner block
text = re.sub(
    r'if schema.__name__ == "StructuredAgentPlan":\s*# Heuristic planner logic\s*if "quotation" in user_prompt:.*?\]\s*\}',
    planner_replacement,
    text,
    flags=re.DOTALL
)

# 2. Update the decision logic to extract action IDs dynamically and handle history
decision_replacement = """        elif schema.__name__ == "DecisionSchema":
            sys_prompt = ""
            user_prompt_dec = ""
            for msg in request.messages:
                if msg.role == "system" and msg.content:
                    sys_prompt += msg.content.lower() + " "
                if msg.role == "user" and msg.content:
                    user_prompt_dec += msg.content.lower() + " "
            
            data = {"actions": []}
            
            import re
            # Extract ready steps from system prompt (e.g. "- id: step_1, type: customer.search")
            ready_steps = re.findall(r'- id:\s*([^,]+),\s*type:\s*([^\n]+)', sys_prompt)
            
            for action_id, action_type in ready_steps:
                action_type = action_type.strip()
                
                if action_type == "customer.search":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"query": "acme"},
                        "reasoning": "Search for customer."
                    })
                elif action_type == "quotation.create_draft":
                    # Try to extract the customer ID from history
                    # In user_prompt_dec, history is provided. Look for "id": "CUST-001..."
                    cust_id = "unknown"
                    org_id = ""
                    match = re.search(r'"id":\s*"([^"]+)"', user_prompt_dec)
                    if match:
                        cust_id = match.group(1)
                    else:
                        # fallback
                        match_org = re.search(r'org_id[^a-z0-9]+([a-f0-9\-]{36})', sys_prompt + user_prompt_dec)
                        if match_org:
                            org_id = match_org.group(1)
                            cust_id = f"CUST-001-{org_id[:8]}"
                            
                    # extract product ID as well? Let's just mock it
                    # But wait, product ID in quotation needs to be PROD-X-{org_id}
                    # We can get org_id from the customer ID if we parsed it, or just use regex.
                    match_org2 = re.search(r'org_id[^a-z0-9]+([a-f0-9\-]{36})', sys_prompt + user_prompt_dec)
                    prod_id = f"PROD-X-{match_org2.group(1)[:8]}" if match_org2 else "PROD-X"
                    
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"customer_id": cust_id, "items": [{"product_id": prod_id, "quantity": 1}]},
                        "reasoning": "Create quotation with resolved customer and products."
                    })
                elif action_type == "observability.get_api_latency":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"time_range": "24h"},
                        "reasoning": "Retrieve latency metrics."
                    })
                elif action_type == "product.search":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"query": "demo"},
                        "reasoning": "Search for products."
                    })
                elif action_type == "pricing.calculate":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"product_id": "PROD-X", "quantity": 1},
                        "reasoning": "Calculate pricing."
                    })"""

# Replace the old decision schema block
text = re.sub(
    r'elif schema\.__name__ == "DecisionSchema":.*?elif "customer\.search" in sys_prompt:.*?\}\s*\]\s*\}',
    decision_replacement,
    text,
    flags=re.DOTALL
)

with open("backend/app/ai/providers/heuristic.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Rewrote heuristic provider")
