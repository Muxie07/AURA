import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import jsonschema  # type: ignore
import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ApprovalRequest, ApprovalStatus
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyContext, PolicyDecision
from app.tools.audit import check_idempotency_key, persist_tool_audit
from app.tools.errors import (
    ToolAuthorizationError,
    ToolCircuitBreakerError,
    ToolError,
    ToolNotFoundError,
)
from app.tools.executor import BaseToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition, ToolResult

logger = structlog.get_logger(__name__)

# Simple in-memory circuit breaker
_CIRCUIT_BREAKERS: dict[str, dict[str, Any]] = {}

def check_circuit_breaker(tool_name: str) -> None:
    cb = _CIRCUIT_BREAKERS.get(tool_name)
    if not cb:
        return
    if cb["failures"] >= 5:
        if (time.time() - cb["last_failure"]) < 60:
            raise ToolCircuitBreakerError(f"Circuit open for tool {tool_name}")
        else:
            # Half-open, reset
            cb["failures"] = 0

def record_circuit_breaker_result(tool_name: str, success: bool) -> None:
    if tool_name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[tool_name] = {"failures": 0, "last_failure": 0}
    if success:
        _CIRCUIT_BREAKERS[tool_name]["failures"] = 0
    else:
        _CIRCUIT_BREAKERS[tool_name]["failures"] += 1
        _CIRCUIT_BREAKERS[tool_name]["last_failure"] = time.time()


class ApprovalRequiredError(Exception):
    def __init__(self, reason: str, args_hash: str):
        self.reason = reason
        self.args_hash = args_hash


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseToolExecutor] = {}
        self.mcp_initialized = False

    async def ensure_mcp_initialized(self, _organization_id) -> None:
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
        self, db: AsyncSession, name: str, arguments: dict[str, Any], context: ToolContext
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

        # Hash arguments
        clean_args = {k: v for k, v in arguments.items() if not k.startswith("_")}
        canonical = json.dumps(clean_args, sort_keys=True, separators=(",", ":"), default=str)
        args_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # Idempotency key derived server-side
        if definition.idempotent:
            context.idempotency_key = hashlib.sha256(
                f"{context.organization_id}:{context.agent_run_id}:{context.execution_id}:{name}:{args_hash}".encode()
            ).hexdigest()
        else:
            context.idempotency_key = None

        # Policy Engine Evaluation
        policy_ctx = PolicyContext(
            organization_id=context.organization_id,
            user_id=context.user_id,
            tool_name=name,
            risk_level=definition.risk_level,
            arguments=clean_args,
            permissions=["tools:read", "tools:write", "tools:external"], # TODO inject from context
        )

        policy_decision = PolicyEngine.evaluate(policy_ctx)

        if policy_decision.decision == PolicyDecision.DENY:
            raise ToolAuthorizationError(f"Policy Denied: {policy_decision.reason}")

        if policy_decision.decision == PolicyDecision.REQUIRE_APPROVAL:
            # Check DB for consumed/approved status
            approval_stmt = sa.text("""
                UPDATE approval_requests
                SET status = 'executed', updated_at = :now
                WHERE agent_run_id = :run_id 
                  AND tool_name = :tool_name 
                  AND status = 'approved'
                  AND args_hash = :args_hash
                  AND expires_at > :now
                  AND organization_id = :org_id
                RETURNING id
            """)
            result = await db.execute(approval_stmt, {
                "now": datetime.now(UTC),
                "run_id": context.agent_run_id,
                "tool_name": name,
                "args_hash": args_hash,
                "org_id": context.organization_id
            })
            approved_id = result.scalar_one_or_none()
            if not approved_id:
                # Need to check if there is a pending one
                pending = await db.scalar(
                    sa.select(ApprovalRequest).where(
                        ApprovalRequest.agent_run_id == context.agent_run_id,
                        ApprovalRequest.tool_name == name,
                        ApprovalRequest.status == ApprovalStatus.PENDING
                    )
                )
                if pending:
                    # Still waiting
                    raise ApprovalRequiredError(reason=policy_decision.reason, args_hash=args_hash)

                # Check if denied
                denied = await db.scalar(
                    sa.select(ApprovalRequest).where(
                        ApprovalRequest.agent_run_id == context.agent_run_id,
                        ApprovalRequest.tool_name == name,
                        ApprovalRequest.status == ApprovalStatus.DENIED
                    )
                )
                if denied:
                    raise ToolAuthorizationError("Policy Denied: Action was rejected by human approver")

                # Need a new approval
                raise ApprovalRequiredError(reason=policy_decision.reason, args_hash=args_hash)

        # 3. Idempotency Check (DB hit)
        if definition.idempotent and context.idempotency_key:
            existing_audit = await check_idempotency_key(
                db, context.organization_id, context.idempotency_key
            )
            if existing_audit:
                logger.info("tool.execution.idempotent_hit", tool_name=name)
                return ToolResult(
                    status="succeeded",
                    result={"_idempotency_hit": True, "message": "Idempotent execution hit."},
                )

        # Write started audit row BEFORE executing WRITE/EXTERNAL
        is_write = definition.risk_level in [RiskLevel.WRITE, RiskLevel.EXTERNAL_SIDE_EFFECT]
        audit_id = None
        if is_write:
            audit_id = await persist_tool_audit(
                db=db,
                context=context,
                definition=definition,
                arguments=clean_args,
                started_at=started_at,
                completed_at=None,
                duration_ms=0,
                result=ToolResult(status="failed", message="Started"),
                input_hash=args_hash,
                status="running"
            )
            await db.commit() # Ensure it's durable before side effects

        # Circuit breaker check
        check_circuit_breaker(name)

        # 4. Executing (with retries and exponential backoff for read/idempotent)
        max_retries = 3 if (definition.risk_level == RiskLevel.READ or definition.idempotent) else 0
        attempts = 0
        result = None

        while attempts <= max_retries:
            attempts += 1
            try:
                # executor handles timeout via definition.timeout_seconds
                result = await executor.execute(clean_args, context)
                record_circuit_breaker_result(name, True)
                break
            except ToolError as e:
                record_circuit_breaker_result(name, False)
                if e.retryable and attempts <= max_retries:
                    await asyncio.sleep(2 ** attempts)
                    continue
                result = ToolResult(
                    status="failed", error_type=e.error_type, message=e.message, retryable=e.retryable
                )
                break
            except Exception:
                record_circuit_breaker_result(name, False)
                if attempts <= max_retries:
                    await asyncio.sleep(2 ** attempts)
                    continue
                result = ToolResult(
                    status="failed",
                    error_type="unknown_error",
                    message="An unexpected error occurred.",
                    retryable=False,
                )
                break

        # Result size cap (prevent massive LLM context explosion)
        if result and result.result:
            result_str = json.dumps(result.result, default=str)
            if len(result_str) > 50000: # 50k chars max
                result.result = {"error": "Result size exceeded 50000 characters. Consider refining your search.", "truncated_preview": result_str[:1000]}

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        if result.status == "succeeded":
            logger.info("tool.execution.succeeded", tool_name=name, duration_ms=duration_ms)
        else:
            logger.error("tool.execution.failed", tool_name=name, error=result.message)

        # Final audit persist (update if write, create if read)
        await persist_tool_audit(
            db=db,
            context=context,
            definition=definition,
            arguments=clean_args,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            duration_ms=duration_ms,
            result=result,
            input_hash=args_hash,
            status=result.status,
            existing_audit_id=audit_id
        )

        return result
