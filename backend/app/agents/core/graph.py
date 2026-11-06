from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog

from app.agents.core.limits import limits
from app.agents.core.nodes import BaseNode
from app.agents.core.state import AgentNodeState, AgentState, FailureCategory

logger = structlog.get_logger(__name__)


class WorkflowGraph:
    """Explicit state machine / graph for agent execution."""

    def __init__(self) -> None:
        self.nodes: dict[AgentNodeState, BaseNode] = {}
        self.transitions: dict[AgentNodeState, Callable[[AgentState], AgentNodeState]] = {}

    def add_node(self, state_key: AgentNodeState, node: BaseNode) -> None:
        self.nodes[state_key] = node

    def add_transition(
        self, from_state: AgentNodeState, transition_func: Callable[[AgentState], AgentNodeState]
    ) -> None:
        self.transitions[from_state] = transition_func

    async def run(self, state: AgentState, **kwargs: Any) -> AgentState:
        """Runs the state machine until a terminal state or limits are reached."""

        terminal_states = {
            AgentNodeState.COMPLETED,
            AgentNodeState.FAILED,
            AgentNodeState.CANCELLED,
            AgentNodeState.TIMEOUT,
            AgentNodeState.WAITING,
        }

        start_time = datetime.now(UTC)

        while state.status not in terminal_states:
            state.iteration_count += 1

            # 1. Limit Checks
            if state.iteration_count > limits.max_agent_iterations:
                state.add_error(
                    category=FailureCategory.TIMEOUT,
                    message=f"Agent exceeded maximum iterations ({limits.max_agent_iterations})",
                )
                state.status = AgentNodeState.TIMEOUT
                break

            print(f"DEBUG GRAPH loop elapsed: {type(datetime.now)} {type(start_time)}")
            elapsed_seconds = (datetime.now(UTC) - start_time).total_seconds()
            if elapsed_seconds > limits.agent_timeout_seconds:
                state.add_error(
                    category=FailureCategory.TIMEOUT,
                    message=f"Agent exceeded maximum time ({limits.agent_timeout_seconds}s)",
                )
                state.status = AgentNodeState.TIMEOUT
                break

            current_status = state.status
            # 2. Get Current Node
            current_node = self.nodes.get(current_status)
            if not current_node:
                state.add_error(
                    category=FailureCategory.BUSINESS_RULE,
                    message=f"No node registered for state {current_status}",
                )
                state.status = AgentNodeState.FAILED
                break

            # 3. Execute Node
            try:
                node_start = datetime.now(UTC)
                tracer = kwargs.get("tracer")
                if tracer:
                    await tracer.record_event(
                        event_type="NODE_STARTED",
                        component=current_node.name,
                        metadata={"state": current_status},
                    )
                import asyncio

                # Implement per-node timeout. A single node should not hang indefinitely.
                state = await asyncio.wait_for(
                    current_node.execute(state, **kwargs),
                    timeout=30.0,  # 30 seconds max per node
                )
                state.updated_at = datetime.now(UTC)
                if tracer:
                    duration_ms = int((datetime.now(UTC) - node_start).total_seconds() * 1000)
                    await tracer.record_event(
                        event_type="NODE_COMPLETED",
                        component=current_node.name,
                        metadata={"new_state": state.status},
                        duration_ms=duration_ms,
                    )
            except TimeoutError:
                logger.error("graph_node_timeout", state=current_status)
                state.add_error(
                    category=FailureCategory.TIMEOUT,
                    message="AURA couldn't complete that request right now. Please try again.",
                )
                state.status = AgentNodeState.TIMEOUT
                break
            except Exception as e:
                logger.error("graph_node_error", error=str(e), state=current_status)
                state.add_error(
                    category=FailureCategory.UNKNOWN, message=f"Node execution failed: {e}"
                )
                state.status = AgentNodeState.FAILED
                break

            # 4. Transition (if state wasn't mutated by the node)
            if state.status == current_status and state.status not in terminal_states:
                transition_func = self.transitions.get(current_status)
                if transition_func:
                    next_state = transition_func(state)
                    state.status = next_state
                else:
                    # No transition defined, halt
                    state.add_error(
                        category=FailureCategory.BUSINESS_RULE,
                        message=f"No transition defined from state {current_status}",
                    )
                    state.status = AgentNodeState.FAILED
                    break

        return state
