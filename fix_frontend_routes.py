import os

paths = [
    "frontend/src/app/page.tsx",
    "frontend/src/app/agents/page.tsx",
    "frontend/src/app/agents/[id]/page.tsx",
    "frontend/src/app/conversations/page.tsx",
    "frontend/src/app/observability/page.tsx",
    "frontend/src/app/tools/page.tsx"
]

for p in paths:
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("'/agent/runs", "'/runs")
        text = text.replace("`/agent/runs", "`/runs")
        text = text.replace("'/agent/approvals", "'/approvals")
        text = text.replace("`/agent/approvals", "`/approvals")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

print("Frontend routes normalized to canonical endpoints")
