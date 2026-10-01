import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.tools.errors import ToolExecutionError, ToolTimeoutError
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult

logger = structlog.get_logger(__name__)

class BaseToolExecutor:
    """Base class for any tool executor (Internal or MCP)."""
    def __init__(self, definition: ToolDefinition):
        self.definition = definition

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        raise NotImplementedError("Must implement execute()")

class InternalToolExecutor(BaseToolExecutor):
    """Executes a local Python function as a tool."""
    def __init__(self, definition: ToolDefinition, handler: Callable[[dict[str, Any], ToolContext], Awaitable[dict[str, Any]]]):
        super().__init__(definition)
        self.handler = handler

    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        # 1. Validation happens before calling this (in the registry/lifecycle)
        # 2. Dry run simulation
        if context.dry_run:
            if self.definition.risk_level in [RiskLevel.WRITE, RiskLevel.EXTERNAL_SIDE_EFFECT]:
                return ToolResult(
                    status="succeeded",
                    result={"_dry_run": True, "message": f"Simulated {self.definition.name}"}
                )
            # READ tools can execute even in dry run if we want, but let's just return a generic
            # or actually execute it if we know it's safe. For simplicity, we just execute READ.
            if self.definition.risk_level != RiskLevel.READ:
                return ToolResult(
                    status="succeeded",
                    result={"_dry_run": True}
                )

        # 3. Timeouts
        try:
            result = await asyncio.wait_for(
                self.handler(arguments, context),
                timeout=self.definition.timeout_seconds
            )
            return ToolResult(status="succeeded", result=result)
        except TimeoutError as e:
            raise ToolTimeoutError(f"Tool {self.definition.name} timed out after {self.definition.timeout_seconds}s") from e
        except Exception as e:
            # We wrap unexpected errors, let ToolError subclasses bubble
            from app.tools.errors import ToolError
            if isinstance(e, ToolError):
                raise
            raise ToolExecutionError(str(e)) from e
