import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog

from app.agents.core.nodes import BaseNode
from app.agents.core.state import ActionHistoryItem, AgentNodeState, AgentState, FailureCategory
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolContext

logger = structlog.get_logger(__name__)


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
        if hasattr(self.registry, "ensure_utcp_initialized") and db:
            await self.registry.ensure_utcp_initialized(state.organization_id, db=db)
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
                result = await self.registry.execute(
                    db, action.action_type, action.arguments, context
                )

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
                        ApprovalRequest.status == ApprovalStatus.PENDING,
                    )
                )
                if not existing:
                    clean_args = {
                        k: v for k, v in action.arguments.items() if not k.startswith("_")
                    }
                    now_utc = datetime.now(timezone.utc)
                    expires_utc = now_utc + timedelta(hours=24)

                    # Extract customer/company info if present
                    company_name = (
                        clean_args.get("company_name")
                        or clean_args.get("customer_name")
                        or "Enterprise Client"
                    )
                    recipient_email = (
                        clean_args.get("recipient") or clean_args.get("customer_email") or ""
                    )
                    total_val = clean_args.get("total") or clean_args.get("amount") or "N/A"
                    disc_pct = clean_args.get("discount_percent", 0.0)

                    # Build structured, auditable business action record (Phase 2 requirement)
                    structured_details = {
                        "action_name": action.action_type,
                        "company_name": company_name,
                        "business_objective": clean_args.get("business_objective")
                        or f"Execute business operation: {action.action_type} for {company_name}",
                        "explanation": clean_args.get("explanation")
                        or f"AURA autonomous agent has formulated a commercial transaction for '{company_name}' that requires governance authorization.",
                        "why_necessary": clean_args.get("why_necessary")
                        or f"Operational policy threshold reached: {e.reason or 'Risk classification check'}",
                        "supporting_evidence": {
                            "client": company_name,
                            "product_model": clean_args.get("model_number")
                            or clean_args.get("items")
                            or "Commercial Catalog Items",
                            "discount_requested": f"{disc_pct}%"
                            if disc_pct
                            else "Standard Pricing",
                            "catalog_source": "Enterprise Master Catalog & Rate Cards",
                            "policy_basis": e.reason or "Enterprise Risk Management Standard",
                        },
                        "target_recipient": recipient_email or company_name,
                        "exact_parameters": clean_args,
                        "financial_impact": f"Total Value: ${total_val}, Discount: {disc_pct}%"
                        if (disc_pct or total_val != "N/A")
                        else "Commercial External Action",
                        "operational_impact": "Dispatches official quotation to customer and updates commercial records.",
                        "risks_and_uncertainties": "Non-reversible customer-facing commitment once dispatched.",
                        "approval_policy": e.reason
                        or "Human-in-the-Loop Commercial Governance Gate",
                        "request_timestamp": now_utc.isoformat(),
                        "expiration_timestamp": expires_utc.isoformat(),
                        "execution_status": "AWAITING_APPROVAL",
                        **clean_args,
                    }

                    action_summary_text = (
                        f"Send Quotation to {company_name}"
                        if "quotation" in action.action_type
                        else f"Execute {action.action_type}"
                    )
                    if e.reason:
                        action_summary_text += f": {e.reason}"

                    approval = ApprovalRequest(
                        agent_run_id=state.run_id,
                        organization_id=state.organization_id,
                        tool_name=action.action_type,
                        action_summary=action_summary_text,
                        action_details=structured_details,
                        args_hash=e.args_hash,
                        status=ApprovalStatus.PENDING,
                        expires_at=expires_utc,
                    )
                    db.add(approval)
                    await db.flush()

                    # Trigger Email Notification with 1-click In-Email review and authorization
                    try:
                        from app.services.email_service import EmailNotificationService

                        email_record = await EmailNotificationService.send_approval_request_email(
                            approval_id=approval.id,
                            tool_name=action.action_type,
                            action_summary=action_summary_text,
                            action_details=structured_details,
                            reason=e.reason,
                            recipient_email=None,  # approver comes from AURA_APPROVAL_EMAIL, not the customer
                            agent_run_id=state.run_id,
                            organization_id=state.organization_id,
                        )
                        approval.action_details = {
                            **approval.action_details,
                            "email_delivery": {
                                "status": email_record.get("status"),
                                "provider": email_record.get("delivery_provider"),
                                "error": email_record.get("delivery_error"),
                            },
                        }
                        if email_record.get("status") != "DELIVERED":
                            logger.error(
                                "approval_email_not_delivered",
                                approval_id=str(approval.id),
                                status=email_record.get("status"),
                                error=email_record.get("delivery_error"),
                            )
                    except Exception as email_err:
                        logger.warning("failed_to_dispatch_approval_email", error=str(email_err))
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
