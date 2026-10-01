for path in ["backend/tests/tools/test_customer_tools.py", "backend/tests/tools/test_quotation_tools.py"]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    text = text.replace("run_id=uuid.uuid4()", "agent_run_id=uuid.uuid4(), execution_id=uuid.uuid4()")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
print("Fixed fixtures")
