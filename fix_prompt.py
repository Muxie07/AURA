with open("backend/app/agents/planning/planner.py", "r", encoding="utf-8") as f:
    text = f.read()

old_prompt = """
        system_prompt = (
            "You are the AURA Planning Agent.\\n"
            "Analyze the user's request and break it down into a structured execution plan.\\n"
            "Possible step types include: retrieve_customer, retrieve_product, retrieve_pricing, create_quotation, etc.\\n"
            "Do NOT output a generic conversational plan. Be highly specific."
        )
"""

new_prompt = """
        system_prompt = (
            "You are the AURA Planning Agent.\\n"
            "Analyze the user's request and break it down into a structured execution plan.\\n"
            "Possible step types include: retrieve_customer, retrieve_product, retrieve_pricing, create_quotation, etc.\\n"
            "Do NOT output a generic conversational plan. Be highly specific.\\n"
            "CRITICAL: If the user asks to investigate API latency, logs, or system observability, you MUST realize that AURA currently has NO connected latency or observability data sources/tools. Do NOT hallucinate tools like 'query_logs'. Instead, return an EMPTY plan (0 steps) with a goal explaining that no latency data source is connected."
        )
"""

text = text.replace(old_prompt.strip(), new_prompt.strip())

with open("backend/app/agents/planning/planner.py", "w", encoding="utf-8") as f:
    f.write(text)
