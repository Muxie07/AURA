import os

path = "frontend/src/app/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix RUNNING filter
text = text.replace("runs.filter(r => r.status === 'RUNNING').length", "runs.filter(r => r.status?.toUpperCase() === 'RUNNING').length")

# Fix systemStatus
text = text.replace("const systemStatus = health ? 'Healthy' : 'Unknown';", "const systemStatus = health?.status === 'ok' ? 'Healthy' : (health ? 'Degraded' : 'Unknown');")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated page.tsx")
