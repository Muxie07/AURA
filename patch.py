import re

with open('backend/app/tools/registry.py', 'r') as f:
    content = f.read()

imports = '''import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import jsonschema
import structlog

from app.database.base import get_session_factory
from app.tools.audit import check_idempotency_key, persist_tool_audit
from app.tools.errors import (
    ToolAuthorizationError,
    ToolError,
    ToolNotFoundError,
    ToolExecutionError,
)
from app.tools.executor import BaseToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult'''

content = re.sub(r'import hashlib.*?from app\.tools\.schemas import ToolContext, ToolDefinition, ToolResult', imports, content, flags=re.DOTALL)

execute_method = '''    async def execute(self, name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        executor = self.get(name)
        definition = executor.definition

        # LIFECYCLE: DISCOVERED -> VALIDATING -> AUTHORIZING -> EXECUTING -> SUCCEEDED/FAILED
        start_time = time.perf_counter()
        started_at = datetime.now(UTC)

        # 1. Validation against JSON Schema
        try:
            jsonschema.validate(instance=arguments, schema=definition.input_schema)
        except jsonschema.ValidationError as e:
            return ToolResult(status="failed", error_type="validation_error", message=f"Input validation failed: {e.message}")

        # 2. Authorization & Tenant Isolation
        if definition.organization_scoped:
            if "organization_id" in arguments:
                arg_org = arguments["organization_id"]
                if str(arg_org) != str(context.organization_id):
                    logger.error("tool.auth.tenant_mismatch", expected=str(context.organization_id), got=str(arg_org))
                    raise ToolAuthorizationError("Tenant isolation violation: tool argument organization_id does not match context.")
            else:
                arguments["organization_id"] = str(context.organization_id)
        
        if definition.requires_approval or definition.risk_level in [RiskLevel.WRITE, RiskLevel.EXTERNAL_SIDE_EFFECT]:
            if not context.approved:
                raise ToolAuthorizationError(f"Tool {name} requires explicit approval before execution.")

        input_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()

        # 3. Idempotency Check
        session_factory = get_session_factory()
        
        if definition.idempotent and context.idempotency_key:
            async with session_factory() as db:
                existing_audit = await check_idempotency_key(db, context.organization_id, context.idempotency_key)
                if existing_audit:
                    logger.info("tool.execution.idempotent_hit", tool_name=name)
                    return ToolResult(status="succeeded", result={"_idempotency_hit": True, "message": "Idempotent execution hit."})

        # 4. Executing
        result = None
        try:
            result = await executor.execute(arguments, context)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info("tool.execution.succeeded", tool_name=name, duration_ms=duration_ms)
            
            async with session_factory() as db:
                await persist_tool_audit(db, context, definition, arguments, started_at, datetime.now(UTC), duration_ms, result, input_hash)
                
            return result
        except ToolError as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("tool.execution.failed", tool_name=name, error=e.message)
            result = ToolResult(status="failed", error_type=e.error_type, message=e.message, retryable=e.retryable)
            
            async with session_factory() as db:
                await persist_tool_audit(db, context, definition, arguments, started_at, datetime.now(UTC), duration_ms, result, input_hash)
            return result
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("tool.execution.failed_unhandled", tool_name=name, error=str(e))
            result = ToolResult(status="failed", error_type="unknown_error", message="An unexpected error occurred.", retryable=False)
            
            async with session_factory() as db:
                await persist_tool_audit(db, context, definition, arguments, started_at, datetime.now(UTC), duration_ms, result, input_hash)
            return result'''

content = re.sub(r'    async def execute\(self, name: str, arguments: dict\[str, Any\], context: ToolContext\) -> ToolResult:.*', execute_method, content, flags=re.DOTALL)

with open('backend/app/tools/registry.py', 'w') as f:
    f.write(content)
