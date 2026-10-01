with open("backend/app/ai/providers/heuristic.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """                elif action_type == "quotation.create_draft":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"customer_id": "CUST-001", "items": [{"product_id": "PROD-X", "quantity": 1}]},
                        "reasoning": "Create quotation."
                    })"""

replacement = """                elif action_type == "quotation.create_draft":
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
                    })"""

target2 = """                elif action_type == "pricing.calculate":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"base_price": "5000.00", "quantity": 1, "discount_percent": "0", "tax_percent": "0"},
                        "reasoning": "Calculate pricing."
                    })"""
replacement2 = """                elif action_type == "pricing.calculate":
                    data["actions"].append({
                        "action_id": action_id,
                        "arguments": {"product_id": "PROD-X", "quantity": 1},
                        "reasoning": "Calculate pricing."
                    })"""

if target in text and target2 in text:
    text = text.replace(target, replacement)
    text = text.replace(target2, replacement2)
    with open("backend/app/ai/providers/heuristic.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Reverted heuristic.py successfully!")
else:
    print("Could not find blocks in heuristic.py")
