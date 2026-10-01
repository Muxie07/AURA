with open('backend/app/agents/core/builtin_nodes.py', 'r') as f: text = f.read()

replan_code = '''
    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        from datetime import datetime, UTC
        
        # 1. Check timeout
        elapsed = (datetime.now(UTC) - state.started_at).total_seconds()
        if elapsed > state.limits.overall_timeout_seconds:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, f"Agent timed out after {elapsed:.1f}s")
            return state

        # 2. Check total tool calls
        if len(state.action_history) >= state.limits.max_tool_calls:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, f"Max tool calls ({state.limits.max_tool_calls}) exceeded")
            return state

        # 3. Determine diagnosis
        last_error = state.errors[-1] if state.errors else None
        is_tool_failure = last_error and last_error.category == FailureCategory.TOOL_FAILURE
        
        if is_tool_failure:
            state.retry_attempts += 1
            if state.retry_attempts > state.limits.max_retries:
                state.status = AgentNodeState.FAILED
                state.add_error(FailureCategory.BUSINESS_RULE, "Max retries exceeded")
                return state
            
        # 4. Enforce Replan limits
        state.replan_attempts += 1
        if state.replan_attempts > state.limits.max_replan_attempts:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, "Max replan attempts exceeded")
            return state

        # 5. Transition to PLANNING
        state.status = AgentNodeState.PLANNING
        state.current_actions = []
        return state
'''

import re
text = re.sub(r'    async def _execute\(self, state: AgentState, \*\*kwargs: Any\) -> AgentState:.*?return state', replan_code.strip('\n'), text, flags=re.DOTALL)
with open('backend/app/agents/core/builtin_nodes.py', 'w', encoding='utf-8') as f: f.write(text)
