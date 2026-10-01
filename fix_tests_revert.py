paths = ["backend/tests/test_phase9_security.py", "backend/tests/test_observability_tool.py"]
for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace('"/api/v1/agent/runs"', '"/api/v1/runs"')
    text = text.replace('"/api/v1/agent/runs/abc/stream"', '"/api/v1/runs/abc/stream"')
    text = text.replace('"/api/v1/agent/runs/stream"', '"/api/v1/runs/stream"')

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
print("Reverted backend tests")
