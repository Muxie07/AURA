with open('backend/app/agents/core/builtin_nodes.py', 'r') as f:
    text = f.read()

text = text.replace('''from app.agents.core.state import (
    ActionHistoryItem,
    AgentState,
    FailureCategory,
)''', '''from app.agents.core.state import (
    ActionHistoryItem,
    AgentState,
    FailureCategory,
    AgentNodeState
)
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
''')

execution_addition = '''        try:
            tool = self.registry.get(action.action_type)
        except ToolNotFoundError:
            state.add_error(FailureCategory.VALIDATION, f"Unknown tool type: {action.action_type}")
            return state
            
        policy_ctx = PolicyContext(
            organization_id=state.organization_id,
            user_id=state.user_id,
            tool_name=tool.name,
            risk_level=tool.definition.risk_level,
            arguments=action.arguments,
            permissions=kwargs.get('permissions', ['tools:read', 'tools:write', 'tools:external']) # Mock permissions if not provided
        )
        
        policy_decision = PolicyEngine.evaluate(policy_ctx)
        
        if policy_decision.decision == PolicyDecision.DENY:
            state.add_error(FailureCategory.AUTHORIZATION, f"Policy Denied: {policy_decision.reason}")
            return state
            
        if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
            state.status = AgentNodeState.WAITING
            return state

        history_item = ActionHistoryItem(
            action=action,
            started_at=start_time
        )
'''

text = text.replace('''        try:
            tool = self.registry.get(action.action_type)
        except ToolNotFoundError:
            state.add_error(FailureCategory.VALIDATION, f"Unknown tool type: {action.action_type}")
            return state

        history_item = ActionHistoryItem(
            action=action,
            started_at=start_time
        )''', execution_addition)

with open('backend/app/agents/core/builtin_nodes.py', 'w') as f:
    f.write(text)
