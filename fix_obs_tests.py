with open("backend/tests/test_observability_tool.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the patch paths - get_redis_client is imported inside the function
# so we need to patch it in the security module
text = text.replace(
    'patch("app.tools.builtin.observability.get_redis_client")',
    'patch("app.security.rate_limit.get_redis_client")'
)

with open("backend/tests/test_observability_tool.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed patch paths")
