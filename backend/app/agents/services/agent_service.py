import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.builtin_nodes import ExecutionNode, FailureNode, FinalizeNode
from app.agents.core.graph import WorkflowGraph
from app.agents.core.retriever import RetrieveNode
from app.agents.core.state import AgentNodeState, AgentState
from app.agents.execution.decision import DecisionNode
from app.agents.planning.planner import PlanNode, UnderstandNode
from app.agents.verification.verifier import DiagnoseNode, ReplanNode, VerificationNode
from app.ai.services.llm import LLMService
from app.database.models import AgentRun, AgentRunStatus, Message, MessageRole, User
from app.knowledge.rag_service import RAGService
from app.observability.trace import AgentTracer
from app.tools.builtin import register_builtin_tools
from app.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class AgentWorkflowService:
    def __init__(self, db: AsyncSession, llm: LLMService, rag: RAGService, mcp_manager=None):
        self.db = db
        self.llm = llm
        self.rag = rag
        self.mcp_manager = mcp_manager

        self.action_registry = ToolRegistry()
        register_builtin_tools(self.action_registry)

        self.graph = self._build_graph()

    async def initialize(self, organization_id: uuid.UUID):
        import os

        mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8000/api/v1/mcp/messages")

        if self.mcp_manager:
            mcp_executors = await self.mcp_manager.discover_tools(mcp_url, str(organization_id))
            for executor in mcp_executors:
                self.action_registry.register(executor)

    def _build_graph(self) -> WorkflowGraph:
        graph = WorkflowGraph()

        # 1. Nodes mapped to states
        graph.add_node(AgentNodeState.CREATED, UnderstandNode(self.llm))
        graph.add_node(AgentNodeState.PLANNING, PlanNode(self.llm))
        graph.add_node(AgentNodeState.RETRIEVING, RetrieveNode(self.db, self.rag))

        # We reuse UNDERSTANDING conceptually as DECISION state
        graph.add_node(AgentNodeState.UNDERSTANDING, DecisionNode(self.llm))

        # READY_TO_EXECUTE acts as the passthrough to EXECUTING
        graph.add_node(AgentNodeState.READY_TO_EXECUTE, ExecutionNode(self.action_registry))
        graph.add_node(AgentNodeState.VERIFYING, VerificationNode(self.llm))
        graph.add_node(AgentNodeState.DIAGNOSING, DiagnoseNode(self.llm))
        graph.add_node(AgentNodeState.REPLANNING, ReplanNode(self.llm))

        graph.add_node(AgentNodeState.COMPLETED, FinalizeNode())

        graph.add_node(AgentNodeState.FAILED, FailureNode())

        # 2. Transitions (only invoked if Node does not explicitly mutate `state.status`)
        graph.add_transition(AgentNodeState.CREATED, lambda s: AgentNodeState.PLANNING)
        graph.add_transition(AgentNodeState.UNDERSTANDING, lambda s: AgentNodeState.PLANNING)
        graph.add_transition(AgentNodeState.PLANNING, lambda s: AgentNodeState.RETRIEVING)
        graph.add_transition(AgentNodeState.RETRIEVING, lambda s: AgentNodeState.UNDERSTANDING)
        graph.add_transition(AgentNodeState.READY_TO_EXECUTE, lambda s: AgentNodeState.VERIFYING)
        graph.add_transition(AgentNodeState.VERIFYING, lambda s: AgentNodeState.UNDERSTANDING)

        return graph

    async def execute_run(self, run_id: uuid.UUID) -> AgentState:
        # Load run
        result = await self.db.execute(sa.select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"AgentRun {run_id} not found")

        run.status = AgentRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await self.db.commit()

        user = await self.db.scalar(sa.select(User).where(User.id == run.user_id))
        org_id = user.organization_id if user else None

        # Check if this run is an approval resumption or cancellation
        from app.database.models import ApprovalRequest, ApprovalStatus

        approval_records = (
            await self.db.scalars(
                sa.select(ApprovalRequest).where(ApprovalRequest.agent_run_id == run_id)
            )
        ).all()

        approved_req = None
        denied_req = None
        for a in approval_records:
            if a.status == ApprovalStatus.APPROVED:
                approved_req = a
            elif a.status == ApprovalStatus.DENIED:
                denied_req = a

        # If human approver explicitly denied the action, complete run gracefully with cancellation notice
        if denied_req and not approved_req:
            rejection_reason = f": {denied_req.denial_reason}" if denied_req.denial_reason else ""
            msg = f"Operation cancelled: Human approval for '{denied_req.action_summary}' was denied{rejection_reason}."
            run.status = AgentRunStatus.COMPLETED
            run.final_response = msg
            run.completed_at = datetime.now(UTC)
            assistant_msg = Message(
                organization_id=run.organization_id,
                conversation_id=run.conversation_id,
                role=MessageRole.ASSISTANT,
                content=msg,
                agent_run_id=run.id,
            )
            self.db.add(assistant_msg)
            await self.db.commit()

            # Dispatch cancellation completion notice (Phase 6)
            try:
                from app.services.email_service import EmailNotificationService

                await EmailNotificationService.send_completion_notification_email(
                    approval_id=denied_req.id,
                    tool_name=denied_req.tool_name,
                    action_summary=denied_req.action_summary,
                    status="CANCELLED",
                    result={
                        "status": "cancelled",
                        "reason": denied_req.denial_reason or "Human rejected action",
                    },
                    error=denied_req.denial_reason
                    or "Human approver denied execution authorization",
                    agent_run_id=run.id,
                    organization_id=run.organization_id,
                    company_name=(denied_req.action_details or {}).get("company_name"),
                )
            except Exception as comp_err:
                logger.warning("failed_to_dispatch_cancellation_email", error=str(comp_err))
            return AgentState(
                run_id=run.id,
                organization_id=org_id,
                user_id=run.user_id,
                conversation_id=run.conversation_id,
                original_request=run.user_request,
                status=AgentNodeState.COMPLETED,
                final_response=msg,
            )

        # Rehydrate from checkpoint if resuming an approved execution
        checkpoint = (run.plan or {}).get("_checkpoint") if isinstance(run.plan, dict) else None
        if approved_req and checkpoint:
            logger.info(
                "resuming_agent_run_from_approval_checkpoint",
                run_id=str(run.id),
                tool=approved_req.tool_name,
            )
            from app.agents.core.state import ActionHistoryItem, AgentAction, AgentPlan

            restored_plan = (
                AgentPlan.model_validate(checkpoint["plan"]) if checkpoint.get("plan") else None
            )
            restored_actions = [
                AgentAction.model_validate(act) for act in checkpoint.get("current_actions", [])
            ]
            restored_history = []
            for h in checkpoint.get("action_history", []):
                try:
                    act = AgentAction.model_validate(h["action"])
                    s_at = datetime.fromisoformat(h["started_at"]) if h.get("started_at") else None
                    c_at = (
                        datetime.fromisoformat(h["completed_at"]) if h.get("completed_at") else None
                    )
                    restored_history.append(
                        ActionHistoryItem(
                            action=act,
                            started_at=s_at,
                            completed_at=c_at,
                            result=h.get("result"),
                            error=None,
                        )
                    )
                except Exception:
                    pass

            state = AgentState(
                run_id=run.id,
                organization_id=org_id,
                user_id=run.user_id,
                conversation_id=run.conversation_id,
                original_request=run.user_request,
                status=AgentNodeState.READY_TO_EXECUTE,
                plan=restored_plan,
                current_actions=restored_actions,
                action_history=restored_history,
                retrieved_context=checkpoint.get("retrieved_context", []),
                iteration_count=checkpoint.get("iteration_count", 0),
                replans=checkpoint.get("replans", 0),
            )
        else:
            state = AgentState(
                run_id=run.id,
                organization_id=org_id,
                user_id=run.user_id,
                conversation_id=run.conversation_id,
                original_request=run.user_request,
                status=AgentNodeState.CREATED,
            )

        tracer = AgentTracer(db=self.db, run_id=run.id, organization_id=org_id)
        import asyncio

        from app.config.settings import get_settings

        settings = get_settings()

        try:
            # Execute Graph
            state = await asyncio.wait_for(
                self.graph.run(
                    state,
                    tracer=tracer,
                    db=self.db,
                    permissions=["tools:read", "tools:write", "tools:external"],
                ),
                timeout=settings.aura_agent_timeout_seconds,
            )

            # Persist back

            run.iteration_count = state.iteration_count
            run.final_response = state.final_response
            run.tool_call_count = len(state.action_history)

            if state.status == AgentNodeState.COMPLETED:
                run.status = AgentRunStatus.COMPLETED
            elif state.status == AgentNodeState.WAITING:
                run.status = AgentRunStatus.AWAITING_APPROVAL
                # We do NOT mark completed_at for WAITING
            else:
                run.status = AgentRunStatus.FAILED
                if state.errors:
                    run.error_message = state.errors[-1].message

            if state.status == AgentNodeState.WAITING:
                run.status = AgentRunStatus.AWAITING_APPROVAL
                # Save execution snapshot so resumption resumes cleanly
                checkpoint = {
                    "status": state.status.value,
                    "plan": state.plan.model_dump() if state.plan else None,
                    "current_actions": [a.model_dump() for a in state.current_actions],
                    "action_history": [
                        {
                            "action": h.action.model_dump(),
                            "started_at": h.started_at.isoformat() if h.started_at else None,
                            "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                            "result": h.result,
                            "error": h.error.model_dump() if h.error else None,
                        }
                        for h in state.action_history
                    ],
                    "retrieved_context": state.retrieved_context,
                    "iteration_count": state.iteration_count,
                    "replans": state.replans,
                }
                base_plan = state.plan.model_dump() if state.plan else {}
                base_plan["_checkpoint"] = checkpoint
                run.plan = base_plan
            elif state.plan:
                base_plan = state.plan.model_dump()
                base_plan.pop("_checkpoint", None)
                run.plan = base_plan

            if run.status != AgentRunStatus.AWAITING_APPROVAL:
                run.completed_at = datetime.now(UTC)

            if run.status == AgentRunStatus.COMPLETED and run.final_response:
                assistant_msg = Message(
                    organization_id=run.organization_id,
                    conversation_id=run.conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=run.final_response,
                    agent_run_id=run.id,
                )
                self.db.add(assistant_msg)
            elif run.status == AgentRunStatus.FAILED:
                msg_content = (
                    run.error_message
                    if run.error_message and run.error_message.startswith("AURA")
                    else f"AURA encountered an error: {run.error_message}"
                )
                assistant_msg = Message(
                    organization_id=run.organization_id,
                    conversation_id=run.conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=msg_content,
                    agent_run_id=run.id,
                )
                self.db.add(assistant_msg)

            await self.db.commit()

            # Phase 6: Dispatch completion notification email for approved executions
            if approved_req:
                try:
                    from app.services.email_service import EmailNotificationService

                    tool_result = None
                    for h in reversed(state.action_history):
                        if h.action.action_type == approved_req.tool_name:
                            tool_result = h.result
                            break
                    if not tool_result:
                        tool_result = state.final_response

                    await EmailNotificationService.send_completion_notification_email(
                        approval_id=approved_req.id,
                        tool_name=approved_req.tool_name,
                        action_summary=approved_req.action_summary,
                        status="COMPLETED" if run.status == AgentRunStatus.COMPLETED else "FAILED",
                        result=tool_result,
                        error=run.error_message,
                        agent_run_id=run.id,
                        organization_id=run.organization_id,
                        company_name=(approved_req.action_details or {}).get("company_name"),
                    )
                except Exception as comp_err:
                    logger.warning("failed_to_dispatch_completion_email", error=str(comp_err))

            return state

        except BaseException as e:
            logger.error("agent_run_failed", error=str(e), run_id=str(run_id))
            run.status = AgentRunStatus.FAILED
            run.error_message = f"Critical engine failure: {e}"
            run.completed_at = datetime.now(UTC)

            assistant_msg = Message(
                organization_id=run.organization_id,
                conversation_id=run.conversation_id,
                role=MessageRole.ASSISTANT,
                content=f"AURA encountered a critical error during execution: {e}",
                agent_run_id=run.id,
            )
            self.db.add(assistant_msg)

            await self.db.commit()
            raise

    async def aclose(self):
        if hasattr(self, "mcp_manager"):
            await self.mcp_manager.close()
