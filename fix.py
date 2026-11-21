import re

with open('backend/app/database/models.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix ToolExecutionAuditclass
code = code.replace('class ToolExecutionAuditclass ToolExecutionAudit', 'class ToolExecutionAudit')

# Fix indentation
lines = code.split('\n')
for i, line in enumerate(lines):
    if line.strip().startswith('__table_args__ = (sa.Index("ix_conv_org_created"'):
        lines[i] = '    ' + line.strip()
    elif line.strip().startswith('__table_args__ = (sa.Index("ix_agent_run_org_created"'):
        lines[i] = '    ' + line.strip()
    elif line.strip().startswith('__table_args__ = (sa.Index("ix_audit_ev_org_created"'):
        lines[i] = '    ' + line.strip()

with open('backend/app/database/models.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
