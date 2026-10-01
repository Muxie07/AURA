import re

with open('app/agents/core/builtin_nodes.py', 'r') as f: text = f.read()

new_exec = '''
    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if not state.current_action:
            state.add_error(FailureCategory.BUSINESS_RULE, "ExecutionNode called without a current_action.")
            return state

        action = state.current_action
        
        # Build ToolContext
        import uuid
        context = ToolContext(
            organization_id=state.organization_id,
            agent_run_id=state.run_id,
            execution_id=uuid.uuid4().hex,
            dry_run=False,
            idempotency_key=action.arguments.get('_idempotency_key')
        )
        
        start_time = datetime.now(timezone.utc)
        
        from app.tools.errors import ToolNotFoundError
        try:
            tool = self.registry.get(action.action_type)
        except ToolNotFoundError:
            state.add_error(FailureCategory.VALIDATION, f"Unknown tool type: {action.action_type}")
            return state

        history_item = ActionHistoryItem(
            action=action,
            started_at=start_time
        )

        # Execute
        result = await self.registry.execute(action.action_type, action.arguments, context)
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        history_item.completed_at = end_time

        if result.status == "failed":
            state.add_error(FailureCategory.TOOL_FAILURE, str(result.message))
            history_item.error = state.errors[-1]
        else:
            history_item.result = result.result

        state.action_history.append(history_item)
        
        # Persist audit if db is available
        db = kwargs.get('db')
        if db:
            import hashlib
            import json
            input_hash = hashlib.sha256(json.dumps(action.arguments, sort_keys=True).encode()).hexdigest()
            await persist_tool_audit(
                db=db,
                context=context,
                definition=tool.definition,
                arguments=action.arguments,
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                result=result,
                input_hash=input_hash
            )
            
        return state
'''

# Find the start of _execute and the start of VerificationNode
start_idx = text.find('async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:')
end_idx = text.find('class VerificationNode(BaseNode):')

text = text[:start_idx] + new_exec.lstrip() + '\n\n' + text[end_idx:]
text = text.replace('from datetime import datetime, UTC', 'from datetime import datetime, timezone\nUTC = timezone.utc')

with open('app/agents/core/builtin_nodes.py', 'w') as f: f.write(text)
