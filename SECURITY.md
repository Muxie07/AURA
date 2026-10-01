# AURA Security Model

AURA implements defense-in-depth across the AI execution lifecycle.

## Tenant Isolation
- **Strict Row-Level Logic**: Every repository query forces `WHERE organization_id = :org_id`.
- **JWT Context**: Authentication securely maps JWT claims directly to `organization_id` ensuring the context cannot be spoofed.
- **Trace Boundaries**: Observability metrics, replays, and incident logs will automatically drop queries attempting cross-tenant reads.

## Policy Engine
Tools declare a `RiskLevel`. High-risk tools (e.g. `send_email`, `execute_transaction`) dynamically drop into `WAITING` state, emitting an `ApprovalRequest` to the front-end requiring a Human-in-the-Loop override.

## AI Safety Evaluations
Every run yields a `SafetyScore`:
- Prompt Injection Detection (Jailbreaks, System Overrides)
- Unauthorized Tool Invocation (RBAC checking)
- Verification success bounding

## Idempotency
Tool executions receive an `idempotency_key` via LLM parameter injection, preventing redundant network requests in async parallel batches.
