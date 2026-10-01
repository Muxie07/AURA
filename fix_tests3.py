for path in ["backend/tests/tools/test_customer_tools.py", "backend/tests/tools/test_quotation_tools.py"]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    text = text.replace("res[\"customers\"]", "res.data[\"customers\"]")
    text = text.replace("res_cust[\"customers\"]", "res_cust.data[\"customers\"]")
    text = text.replace("res[\"status\"]", "res.data[\"status\"]")
    text = text.replace("res[\"quotation_id\"]", "res.data[\"quotation_id\"]")
    
    # Also replace ValueError with ToolExecutionError
    text = text.replace("ValueError", "ToolExecutionError")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("from app.tools.errors import ToolExecutionError\n" + text)
print("Fixed result access")
