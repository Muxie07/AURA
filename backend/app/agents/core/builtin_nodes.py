import asyncio
from datetime import UTC, datetime, timezone
from typing import Any

import structlog

from app.agents.core.nodes import BaseNode
from app.agents.core.state import ActionHistoryItem, AgentNodeState, AgentState, FailureCategory
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
from app.tools.audit import persist_tool_audit
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolContext

logger = structlog.get_logger(__name__)
UTC = UTC

class FailureNode(BaseNode):
    @property
    def name(self) -> str:
        return "FailureNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        from datetime import UTC, datetime

        # 1. Check timeout
        print("DEBUG elapsed:", type(datetime.now), type(state.started_at), flush=True)
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
            state.retry_count += 1
            if state.retry_count > state.limits.max_retries:
                state.status = AgentNodeState.FAILED
                state.add_error(FailureCategory.BUSINESS_RULE, "Max retries exceeded")
                return state

        # 4. Enforce Replan limits
        state.replans += 1
        if state.replans > state.limits.max_replan_attempts:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, "Max replan attempts exceeded")
            return state

        # 5. Transition to PLANNING
        state.status = AgentNodeState.PLANNING
        state.current_actions = []
        return state

class FinalizeNode(BaseNode):
    @property
    def name(self) -> str:
        return "FinalizeNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        from datetime import UTC, datetime

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
            state.retry_count += 1
            if state.retry_count > state.limits.max_retries:
                state.status = AgentNodeState.FAILED
                state.add_error(FailureCategory.BUSINESS_RULE, "Max retries exceeded")
                return state

        # 4. Enforce Replan limits
        state.replans += 1
        if state.replans > state.limits.max_replan_attempts:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, "Max replan attempts exceeded")
            return state

        # 5. Transition to PLANNING
        state.status = AgentNodeState.PLANNING
        state.current_actions = []
        return state

class ExecutionNode(BaseNode):
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    @property
    def name(self) -> str:
        return "ExecutionNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        state.status = AgentNodeState.VERIFYING
        await self.registry.ensure_mcp_initialized(state.organization_id)

        async def execute_action(action):
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
                return

            policy_ctx = PolicyContext(
                organization_id=state.organization_id,
                user_id=state.user_id,
                tool_name=tool.definition.name,
                risk_level=tool.definition.risk_level,
                arguments=action.arguments,
                permissions=kwargs.get('permissions', ['tools:read', 'tools:write', 'tools:external']) # Mock permissions if not provided
            )

            policy_decision = PolicyEngine.evaluate(policy_ctx)

            if policy_decision.decision == PolicyDecision.DENY:
                state.add_error(FailureCategory.AUTHORIZATION, f"Policy Denied: {policy_decision.reason}")
                return

            if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
                db = kwargs.get('db')
                if db:
                    from app.database.models import ApprovalRequest, ApprovalStatus
                    import sqlalchemy as sa
                    existing_approval = await db.scalar(
                        sa.select(ApprovalRequest).where(
                            ApprovalRequest.agent_run_id == state.run_id,
                            ApprovalRequest.tool_name == tool.definition.name,
                        ).order_by(ApprovalRequest.created_at.desc())
                    )
                    
                    if existing_approval:
                        if existing_approval.status == ApprovalStatus.PENDING:
                            state.status = AgentNodeState.WAITING
                            return
                        elif existing_approval.status == ApprovalStatus.DENIED:
                            state.add_error(FailureCategory.AUTHORIZATION, "Policy Denied: Action was rejected by human approver")
                            return
                        elif existing_approval.status == ApprovalStatus.APPROVED:
                            pass # Proceed to execute
                    else:
                        state.status = AgentNodeState.WAITING
                        approval = ApprovalRequest(
                            agent_run_id=state.run_id,
                            tool_name=tool.definition.name,
                            arguments=action.arguments,
                            reason=policy_decision.reason,
                            status=ApprovalStatus.PENDING
                        )
                        db.add(approval)
                        await db.flush()
                        return

            history_item = ActionHistoryItem(action=action, started_at=start_time, completed_at=None, error=None, result=None)

            try:
                result = await tool.execute(action.arguments, context)
            except Exception as e:
                state.add_error(FailureCategory.TOOL_FAILURE, str(e))
                history_item.error = state.errors[-1]
                state.action_history.append(history_item)
                return

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            history_item.completed_at = end_time

            if result.status == "failed":
                state.add_error(FailureCategory.TOOL_FAILURE, str(result.message))
                history_item.error = state.errors[-1]
            else:
                history_item.result = result.result

            state.action_history.append(history_item)

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
                    duration_ms=int(duration_ms),
                    result=result,
                    input_hash=input_hash
                )

        await asyncio.gather(*[execute_action(a) for a in state.current_actions])
        state.current_actions = []
        return state

class VerificationNode(BaseNode):
    def __init__(self, llm: Any):
        self.llm = llm

    @property
    def name(self) -> str:
        return "VerificationNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        if state.errors:
            state.status = AgentNodeState.DIAGNOSING
            return state
        state.status = AgentNodeState.UNDERSTANDING
        return state

class DiagnoseNode(BaseNode):
    def __init__(self, llm: Any):
        self.llm = llm

    @property
    def name(self) -> str:
        return "DiagnoseNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        state.status = AgentNodeState.REPLANNING
        return state

class ReplanNode(BaseNode):
    def __init__(self, llm: Any):
        self.llm = llm

    @property
    def name(self) -> str:
        return "ReplanNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        from datetime import UTC, datetime

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
            state.retry_count += 1
            if state.retry_count > state.limits.max_retries:
                state.status = AgentNodeState.FAILED
                state.add_error(FailureCategory.BUSINESS_RULE, "Max retries exceeded")
                return state

        # 4. Enforce Replan limits
        state.replans += 1
        if state.replans > state.limits.max_replan_attempts:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, "Max replan attempts exceeded")
            return state

        # 5. Transition to PLANNING
        state.status = AgentNodeState.PLANNING
        state.current_actions = []
        return state
