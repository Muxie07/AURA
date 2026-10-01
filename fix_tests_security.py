path = "backend/tests/test_phase9_security.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('"/api/v1/runs"', '"/api/v1/agent/runs"')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated backend security tests")
