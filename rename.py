import re
with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

text = text.replace('@router.post(\"/agent/runs\"', '@router.post(\"/runs\"')
text = text.replace('@router.get(\"/agent/runs\"', '@router.get(\"/runs\"')
text = text.replace('@router.get(\"/agent/runs/{run_id}\"', '@router.get(\"/runs/{run_id}\"')
text = text.replace('@router.get(\"/agent/runs/{run_id}/events\"', '@router.get(\"/runs/{run_id}/events\"')
text = text.replace('@router.get(\"/agent/runs/{run_id}/trace\"', '@router.get(\"/runs/{run_id}/trace\"')
text = text.replace('@router.get(\"/agent/runs/{run_id}/stream\"', '@router.get(\"/runs/{run_id}/stream\"')

text = text.replace('@router.get(\"/agent/approvals\"', '@router.get(\"/approvals\"')
text = text.replace('@router.post(\"/agent/approvals/{approval_id}/approve\"', '@router.post(\"/approvals/{approval_id}/approve\"')
text = text.replace('@router.post(\"/agent/approvals/{approval_id}/reject\"', '@router.post(\"/approvals/{approval_id}/reject\"')

with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)
