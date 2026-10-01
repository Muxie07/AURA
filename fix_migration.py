import re

with open('backend/migrations/versions/20260916_0519_9b12eb5d28bb_phase_6_agent_observability_approvals.py', 'r') as f:
    text = f.read()

# Remove approval_requests creation
text = re.sub(r"    # 3\. Create approval_requests table.*?op\.create_index.*?unique=False\)", "", text, flags=re.DOTALL)
text = re.sub(r"    op\.drop_index.*?op\.drop_table\('approval_requests'\)", "", text, flags=re.DOTALL)

with open('backend/migrations/versions/20260916_0519_9b12eb5d28bb_phase_6_agent_observability_approvals.py', 'w') as f:
    f.write(text)
