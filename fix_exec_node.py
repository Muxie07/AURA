with open('backend/app/agents/core/builtin_nodes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:' in line and 'return "ExecutionNode"' in "".join(new_lines[-4:]):
        new_lines.append(line)
        skip = True
        continue
        
    if skip and 'state.status = AgentNodeState.VERIFYING' in line:
        skip = False
        
    if not skip:
        new_lines.append(line)

with open('backend/app/agents/core/builtin_nodes.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
