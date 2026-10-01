import uuid

# Fix ai.py
ai_path = r'backend/app/api/v1/ai.py'
with open(ai_path, 'r') as f:
    ai_code = f.read()

if '@router.post(\"/classify\", response_model=IntentResult)' in ai_code:
    ai_code = ai_code.replace(
        '@router.post(\"/classify\", response_model=IntentResult)',
        '@router.post(\"/classify\", response_model=IntentResult, dependencies=[Depends(rate_limit_dependency)])'
    )

with open(ai_path, 'w') as f:
    f.write(ai_code)

# Fix agent.py
agent_path = r'backend/app/api/v1/agent.py'
with open(agent_path, 'r') as f:
    agent_code = f.read()

if 'from app.api.deps import CurrentUserDep, DatabaseDep' in agent_code:
    if 'from app.security.rate_limit import rate_limit_dependency' not in agent_code:
        agent_code = agent_code.replace(
            'from app.api.deps import CurrentUserDep, DatabaseDep',
            'from app.api.deps import CurrentUserDep, DatabaseDep\nfrom app.security.rate_limit import rate_limit_dependency'
        )

if '@router.post(\"/agent/runs\", response_model=AgentRunResponse)' in agent_code:
    agent_code = agent_code.replace(
        '@router.post(\"/agent/runs\", response_model=AgentRunResponse)',
        '@router.post(\"/agent/runs\", response_model=AgentRunResponse, dependencies=[Depends(rate_limit_dependency)])'
    )

with open(agent_path, 'w') as f:
    f.write(agent_code)

print('Done patching ai.py and agent.py.')
