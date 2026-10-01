from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.agents.core.state import AgentAction

logger = structlog.get_logger(__name__)


class ActionExecutor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, action: AgentAction, context: dict[str, Any]) -> dict[str, Any]:
        """Executes the action deterministically and safely."""
        pass


class ActionRegistry:
    """Registry to map action types to their safe executors."""

    def __init__(self) -> None:
        self._executors: dict[str, ActionExecutor] = {}

    def register(self, executor: ActionExecutor) -> None:
        self._executors[executor.name] = executor

    def get_executor(self, action_type: str) -> ActionExecutor | None:
        return self._executors.get(action_type)
