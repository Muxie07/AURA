import re

# Fix agent.py
with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()
text = text.replace('@router.post(\"/runs\"', '@router.post(\"/agent/runs\"')
text = text.replace('@router.get(\"/runs\"', '@router.get(\"/agent/runs\"')
text = text.replace('@router.get(\"/runs/{run_id}\"', '@router.get(\"/agent/runs/{run_id}\"')
text = text.replace('@router.get(\"/runs/{run_id}/events\"', '@router.get(\"/agent/runs/{run_id}/events\"')
text = text.replace('@router.get(\"/runs/{run_id}/trace\"', '@router.get(\"/agent/runs/{run_id}/trace\"')
text = text.replace('@router.get(\"/runs/{run_id}/stream\"', '@router.get(\"/agent/runs/{run_id}/stream\"')
text = text.replace('@router.get(\"/approvals\"', '@router.get(\"/agent/approvals\"')
text = text.replace('@router.post(\"/approvals/{approval_id}/approve\"', '@router.post(\"/agent/approvals/{approval_id}/approve\"')
text = text.replace('@router.post(\"/approvals/{approval_id}/reject\"', '@router.post(\"/agent/approvals/{approval_id}/reject\"')
with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)

# Fix conversations/page.tsx
with open('frontend/src/app/conversations/page.tsx', 'r') as f:
    text = f.read()
text = text.replace('/runs', '/agent/runs')
with open('frontend/src/app/conversations/page.tsx', 'w') as f:
    f.write(text)

# Fix approvals/page.tsx
with open('frontend/src/app/approvals/page.tsx', 'r') as f:
    text = f.read()
text = text.replace('/approvals', '/agent/approvals')
with open('frontend/src/app/approvals/page.tsx', 'w') as f:
    f.write(text)

# Fix test_flow.py
with open('test_flow.py', 'r') as f:
    text = f.read()
text = text.replace('/runs', '/agent/runs')
with open('test_flow.py', 'w') as f:
    f.write(text)
