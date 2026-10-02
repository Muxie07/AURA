import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

from app.agents.core.nodes import BaseNode
from app.agents.core.state import ActionHistoryItem, AgentNodeState, AgentState, FailureCategory
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolContext

logger = structlog.get_logger(__name__)
UTC = UTC


class FailureNode(BaseNode):
    @property
    def name(self) -> str:
        return "FailureNode"

    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:

        # 1. Check timeout
        print("DEBUG elapsed:", type(datetime.now), type(state.started_at), flush=True)
        elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        if elapsed > state.limits.overall_timeout_seconds:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, f"Agent timed out after {elapsed:.1f}s")
            return state

        # 2. Check total tool calls
        if len(state.action_history) >= state.limits.max_tool_calls:
            state.status = AgentNodeState.FAILED
            state.add_error(
                FailureCategory.BUSINESS_RULE,
                f"Max tool calls ({state.limits.max_tool_calls}) exceeded",
            )
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

        # 1. Check timeout
        elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        if elapsed > state.limits.overall_timeout_seconds:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, f"Agent timed out after {elapsed:.1f}s")
            return state

        # 2. Check total tool calls
        if len(state.action_history) >= state.limits.max_tool_calls:
            state.status = AgentNodeState.FAILED
            state.add_error(
                FailureCategory.BUSINESS_RULE,
                f"Max tool calls ({state.limits.max_tool_calls}) exceeded",
            )
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

        db = kwargs.get("db")
        if not db:
            raise ValueError("Database session is required for ExecutionNode")

        async def execute_action(action):
            import uuid

            from app.tools.errors import ToolAuthorizationError, ToolNotFoundError
            from app.tools.registry import ApprovalRequiredError

            context = ToolContext(
                organization_id=state.organization_id,
                agent_run_id=state.run_id,
                execution_id=uuid.uuid4().hex,
                dry_run=kwargs.get("dry_run", False),
                user_id=state.user_id,
                idempotency_key=None,
            )

            start_time = datetime.now(timezone.utc)
            history_item = ActionHistoryItem(
                action=action, started_at=start_time, completed_at=None, error=None, result=None
            )

            try:
                result = await self.registry.execute(db, action.action_type, action.arguments, context)

                end_time = datetime.now(timezone.utc)
                history_item.completed_at = end_time

                if result.status == "failed":
                    state.add_error(FailureCategory.TOOL_FAILURE, str(result.message))
                    history_item.error = state.errors[-1]
                else:
                    history_item.result = result.result

                state.action_history.append(history_item)

            except ApprovalRequiredError as e:
                from datetime import timedelta

                import sqlalchemy as sa

                from app.database.models import ApprovalRequest, ApprovalStatus

                state.status = AgentNodeState.WAITING

                existing = await db.scalar(
                    sa.select(ApprovalRequest).where(
                        ApprovalRequest.agent_run_id == state.run_id,
                        ApprovalRequest.tool_name == action.action_type,
                        ApprovalRequest.status == ApprovalStatus.PENDING
                    )
                )
                if not existing:
                    clean_args = {k: v for k, v in action.arguments.items() if not k.startswith('_')}
                    approval = ApprovalRequest(
                        agent_run_id=state.run_id,
                        organization_id=state.organization_id,
                        tool_name=action.action_type,
                        action_summary=f"Execution of {action.action_type}",
                        action_details=clean_args,
                        args_hash=e.args_hash,
                        reason=e.reason,
                        status=ApprovalStatus.PENDING,
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                    )
                    db.add(approval)
                    await db.flush()
                return

            except ToolNotFoundError as e:
                state.add_error(FailureCategory.VALIDATION, str(e))
                history_item.error = state.errors[-1]
                state.action_history.append(history_item)
            except ToolAuthorizationError as e:
                state.add_error(FailureCategory.AUTHORIZATION, str(e))
                history_item.error = state.errors[-1]
                state.action_history.append(history_item)
            except Exception as e:
                state.add_error(FailureCategory.TOOL_FAILURE, str(e))
                history_item.error = state.errors[-1]
                state.action_history.append(history_item)

        await asyncio.gather(*[execute_action(a) for a in state.current_actions])

        if state.status != AgentNodeState.WAITING:
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

        # 1. Check timeout
        elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        if elapsed > state.limits.overall_timeout_seconds:
            state.status = AgentNodeState.FAILED
            state.add_error(FailureCategory.BUSINESS_RULE, f"Agent timed out after {elapsed:.1f}s")
            return state

        # 2. Check total tool calls
        if len(state.action_history) >= state.limits.max_tool_calls:
            state.status = AgentNodeState.FAILED
            state.add_error(
                FailureCategory.BUSINESS_RULE,
                f"Max tool calls ({state.limits.max_tool_calls}) exceeded",
            )
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
