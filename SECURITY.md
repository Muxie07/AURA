# AURA Security Threat Model & Analysis

AURA implements a defense-in-depth architecture, specifically designed to secure an autonomous AI agent against lethal injection attacks, cross-tenant data leaks, and uncontrolled financial spend.

## STRIDE Analysis

- **Spoofing**: Addressed via cryptographically verified `bcrypt` auth, JWT signatures, and isolated `X-Organization-Id` validations ensuring a tenant cannot spoof context.
- **Tampering**: All High-Risk MCP tool executions bind to a SHA-256 hash of their arguments. Any attempt to tamper with args during or after HITL approval rejects the execution.
- **Repudiation**: Enforced via append-only `ToolExecutionAudit` rows containing user context, timestamp, and W3C trace identifiers.
- **Information Disclosure**: Prevented via PostgreSQL Row-Level Security (RLS) policies acting as a secondary firewall beneath the API application layer.
- **Denial of Service**: Mitigated via Redis-backed sliding window rate limits, database `statement_timeout`, and `idle_in_transaction_session_timeout`.
- **Elevation of Privilege**: Mitigated via strict RBAC (Owner/Admin/Member/Viewer) and distinct LLM access privileges enforced by `PolicyEngine`.

## Trust Boundaries
1. **User ↔ API (Frontend to Backend)**: Secured via JWT/Bearer authentication over HTTPS.
2. **Backend ↔ LLM**: External network call secured via API keys over TLS. The LLM is treated as an *untrusted adversary* capable of hallucinations or prompt injections.
3. **API ↔ Database**: Internal VPC boundary. Secured via database user isolation and application-level Row-Level Security contexts.
4. **Agent ↔ Tools (MCP)**: The Model Context Protocol executes over SSE. Tool requests are explicitly scrubbed of `__aura_context` metadata, mitigating poisoning from remote unverified servers.

## "Lethal Trifecta" Prompt Injection
AURA defeats adversarial prompt injections via three layers:
1. **Model Router Blocks**: Deterministic temperature control (`eval_mode`) paired with built-in safety filters rejecting overt malicious directives.
2. **PolicyEngine Sandboxing**: Even if the LLM is hijacked to command `mcp.delete_user`, the `PolicyEngine` enforces `RiskLevel.WRITE`, stalling the execution until cryptographic HITL approval is acquired.
3. **Groundedness Evaluators**: Secondary AI verification intercepts retrieval outputs, mathematically matching citations to chunk source texts to filter fabricated/injected evidence.

## Data Classification
- **Public**: System health `/ping`, OpenAPI schema `/docs`.
- **Internal**: Agent metrics `/metrics` (firewalled internally).
- **Confidential**: Conversation logs, uploaded RAG PDFs (isolated by Organization ID).
- **Highly Restricted**: `api_keys`, `hashed_password`, `AURA_SECRET_KEY`.
