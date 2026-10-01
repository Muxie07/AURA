import re

with open('backend/app/api/v1/runs.py', 'r', encoding='utf-8') as f:
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

with open('backend/app/api/v1/runs.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    front = f.read()
front = front.replace('/agent/runs', '/runs')
with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(front)

with open('frontend/src/app/approvals/page.tsx', 'r', encoding='utf-8') as f:
    appr = f.read()
appr = appr.replace('/agent/approvals', '/approvals')
with open('frontend/src/app/approvals/page.tsx', 'w', encoding='utf-8') as f:
    f.write(appr)

with open('test_flow.py', 'r', encoding='utf-8') as f:
    tf = f.read()
tf = tf.replace('/agent/runs', '/runs')
with open('test_flow.py', 'w', encoding='utf-8') as f:
    f.write(tf)
