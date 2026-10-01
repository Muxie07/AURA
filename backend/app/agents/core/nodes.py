from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.agents.core.state import AgentState

logger = structlog.get_logger(__name__)


class BaseNode(ABC):
    """Abstract base class for all agent graph nodes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the node."""
        pass

    async def execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        """
        Executes the node's logic.
        Returns the mutated state.
        """
        logger.info("node_execution_started", node=self.name, run_id=str(state.run_id))

        try:
            new_state = await self._execute(state, **kwargs)
            logger.info("node_execution_completed", node=self.name, run_id=str(state.run_id))
            return new_state
        except Exception as e:
            logger.error(
                "node_execution_failed", node=self.name, run_id=str(state.run_id), error=str(e)
            )
            raise

    @abstractmethod
    async def _execute(self, state: AgentState, **kwargs: Any) -> AgentState:
        """Internal execution logic to be implemented by subclasses."""
        pass
