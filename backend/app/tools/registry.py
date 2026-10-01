import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import jsonschema  # type: ignore
import structlog

from app.database.base import get_session_factory
from app.tools.audit import check_idempotency_key, persist_tool_audit
from app.tools.errors import (
    ToolAuthorizationError,
    ToolError,
    ToolNotFoundError,
)
from app.tools.executor import BaseToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult

logger = structlog.get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseToolExecutor] = {}
        self.mcp_initialized = False

    async def ensure_mcp_initialized(self, _organization_id) -> None:
        # MCP initialization bypassed to prevent anyio cancel scope crashes
        self.mcp_initialized = True
        return

    def register(self, executor: BaseToolExecutor) -> None:
        name = executor.definition.name
        if name in self._tools:
            raise ValueError(f"Tool {name} is already registered.")
        self._tools[name] = executor
        logger.info("tool.registered", name=name, source=executor.definition.source)

    def get(self, name: str) -> BaseToolExecutor:
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def list_definitions(self) -> list[ToolDefinition]:
        return [ex.definition for ex in self._tools.values()]

    async def execute(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> ToolResult:
        executor = self.get(name)
        definition = executor.definition

        # LIFECYCLE: DISCOVERED -> VALIDATING -> AUTHORIZING -> EXECUTING -> SUCCEEDED/FAILED
        start_time = time.perf_counter()
        started_at = datetime.now(UTC)

        # 1. Validation against JSON Schema
        try:
            jsonschema.validate(instance=arguments, schema=definition.input_schema)
        except jsonschema.ValidationError as e:
            return ToolResult(
                status="failed",
                error_type="validation_error",
                message=f"Input validation failed: {e.message}",
            )

        # 2. Authorization & Tenant Isolation
        if definition.organization_scoped:
            if "organization_id" in arguments:
                arg_org = arguments["organization_id"]
                if str(arg_org) != str(context.organization_id):
                    logger.error(
                        "tool.auth.tenant_mismatch",
                        expected=str(context.organization_id),
                        got=str(arg_org),
                    )
                    raise ToolAuthorizationError(
                        "Tenant isolation violation: tool argument organization_id does not match context."
                    )
            else:
                arguments["organization_id"] = str(context.organization_id)

        if (
            definition.requires_approval
            or definition.risk_level in [RiskLevel.WRITE, RiskLevel.EXTERNAL_SIDE_EFFECT]
        ) and not context.approved:
            raise ToolAuthorizationError(
                f"Tool {name} requires explicit approval before execution."
            )

        input_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()

        # 3. Idempotency Check
        session_factory = None
        try:
            session_factory = get_session_factory()
        except RuntimeError:
            logger.warning("Session factory not initialized. Skipping DB checks.")

        if definition.idempotent and context.idempotency_key and session_factory:
            async with session_factory() as db:
                existing_audit = await check_idempotency_key(
                    db, context.organization_id, context.idempotency_key
                )
                if existing_audit:
                    logger.info("tool.execution.idempotent_hit", tool_name=name)
                    return ToolResult(
                        status="succeeded",
                        result={"_idempotency_hit": True, "message": "Idempotent execution hit."},
                    )

        # 4. Executing
        result = None
        try:
            result = await executor.execute(arguments, context)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info("tool.execution.succeeded", tool_name=name, duration_ms=duration_ms)

            if session_factory:
                async with session_factory() as db:
                    await persist_tool_audit(
                        db,
                        context,
                        definition,
                        arguments,
                        started_at,
                        datetime.now(UTC),
                        duration_ms,
                        result,
                        input_hash,
                    )

            return result
        except ToolError as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("tool.execution.failed", tool_name=name, error=e.message)
            result = ToolResult(
                status="failed", error_type=e.error_type, message=e.message, retryable=e.retryable
            )

            if session_factory:
                async with session_factory() as db:
                    await persist_tool_audit(
                        db,
                        context,
                        definition,
                        arguments,
                        started_at,
                        datetime.now(UTC),
                        duration_ms,
                        result,
                        input_hash,
                    )
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("tool.execution.failed_unhandled", tool_name=name, error=str(e))
            result = ToolResult(
                status="failed",
                error_type="unknown_error",
                message="An unexpected error occurred.",
                retryable=False,
            )

            if session_factory:
                async with session_factory() as db:
                    await persist_tool_audit(
                        db,
                        context,
                        definition,
                        arguments,
                        started_at,
                        datetime.now(UTC),
                        duration_ms,
                        result,
                        input_hash,
                    )
            return result
