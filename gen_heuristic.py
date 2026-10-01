with open("backend/app/ai/providers/heuristic.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_planner = False
in_decision = False
for line in lines:
    if 'if schema.__name__ == "StructuredAgentPlan":' in line:
        in_planner = True
        new_lines.append(line)
        new_lines.append("""            if "quotation" in user_prompt:
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
                }
""")
    elif in_planner and 'elif "latency"' in line:
        in_planner = False
        new_lines.append(line)
    elif 'elif schema.__name__ == "DecisionSchema":' in line:
        in_decision = True
        new_lines.append(line)
        new_lines.append("""            import re
            sys_prompt = ""
            user_prompt_dec = ""
            for msg in request.messages:
                if msg.role == "system" and msg.content:
                    sys_prompt += msg.content.lower() + " "
                if msg.role == "user" and msg.content:
                    user_prompt_dec += msg.content.lower() + " "
            
            data = {"actions": []}
            ready_steps = re.findall(r'- id:\s*([^,]+),\s*type:\s*([^\\n]+)', sys_prompt)
            
            for action_id, action_type in ready_steps:
                action_type = action_type.strip()
                if action_type == "customer.search":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"query": "acme"},
                        "reasoning": "Search for customer."
                    })
                elif action_type == "quotation.create_draft":
                    cust_id = "unknown"
                    org_id = ""
                    match = re.search(r'"id":\s*"([^"]+)"', user_prompt_dec)
                    if match:
                        cust_id = match.group(1)
                    else:
                        match_org = re.search(r'org_id[^a-z0-9]+([a-f0-9\-]{36})', sys_prompt + user_prompt_dec)
                        if match_org:
                            org_id = match_org.group(1)
                            cust_id = f"CUST-001-{org_id[:8]}"
                    match_org2 = re.search(r'org_id[^a-z0-9]+([a-f0-9\-]{36})', sys_prompt + user_prompt_dec)
                    prod_id = f"PROD-X-{match_org2.group(1)[:8]}" if match_org2 else "PROD-X"
                    
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"customer_id": cust_id, "items": [{"product_id": prod_id, "quantity": 1}]},
                        "reasoning": "Create quotation."
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
                    })
""")
    elif in_decision and 'else:' in line and 'data = {"actions": []}' in line:
        in_decision = False
        new_lines.append(line)
    elif not in_planner and not in_decision:
        new_lines.append(line)

with open("backend/app/ai/providers/heuristic.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Rewrote heuristic provider successfully")
