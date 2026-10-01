path = "backend/tests/test_observability_tool.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('"/api/v1/runs"', '"/api/v1/agent/runs"')
text = text.replace('"/api/v1/runs/abc/stream"', '"/api/v1/agent/runs/abc/stream"')
text = text.replace('"/api/v1/runs/stream"', '"/api/v1/agent/runs/stream"')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated backend observability tests")
