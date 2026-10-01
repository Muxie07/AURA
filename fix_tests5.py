path = "backend/tests/tools/test_customer_tools.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text += """
@pytest.mark.asyncio
async def test_multiple_matching_customer_search(mock_context):
    res = await customer_search_tool.execute({"query": "com"}, mock_context)
    assert len(res.result["customers"]) == 2
"""
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Added test for multiple matching")
