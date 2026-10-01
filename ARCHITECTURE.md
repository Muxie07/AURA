# AURA Architecture

This document details the core architectural patterns and data flows that power AURA.

## Agent Execution Graph

AURA's reasoning engine is powered by **LangGraph**. The workflow acts as a cyclical graph:

1. **Router Node**: The LLM (Claude) evaluates the current state, user prompt, and past tool outputs. It decides whether to formulate a final answer or request execution of a specific tool via MCP.
2. **Action Node**: Executes requested tools. If the tool is read-only (e.g., `check_system_status`), it runs immediately.
3. **HITL Interruption**: If a tool is mutating (e.g., `restart_service`), LangGraph throws an `interrupt()`. The state is serialized to Postgres (via `MemorySaver` or Postgres checkpointer), and the graph halts.
4. **Resumption**: Once a human approves the action via the UI, a payload containing the `thread_id` triggers graph resumption, proceeding to tool execution and routing back to the LLM for final synthesis.

## RAG Pipeline (PgVector & Redis)

To provide context-aware remediations, AURA implements a Retrieval-Augmented Generation (RAG) pipeline:

- **Embeddings**: Incident history, architecture docs, and standard operating procedures (SOPs) are embedded and stored in **PostgreSQL using PgVector**.
- **Vector Search**: Before the LLM answers, the orchestrator queries PgVector for semantically similar past incidents.
- **Redis Caching**: Frequently accessed runbooks and query results are cached in **Redis** to reduce latency and database load.

## Model Context Protocol (MCP) Integration

AURA leverages the **Model Context Protocol (MCP)** to standardize tool execution and data retrieval across diverse infrastructure environments:

- **Extensible Tooling**: MCP servers act as plugins, providing access to external APIs (e.g., AWS, Kubernetes, Datadog) without hardcoding integrations into the core agent.
- **Security Boundary**: MCP servers execute in isolated environments, ensuring the agent only accesses authorized resources.

## Multi-Tenancy

AURA is designed to support multiple organizations or teams within a single deployment:

- **Data Isolation**: All database queries (Postgres and PgVector) are scoped by a `tenant_id`, ensuring strict data boundaries between clients.
- **Configuration Management**: Tenant-specific configurations, such as custom MCP endpoints and API keys, are securely managed and loaded at runtime.

## Idempotency Guarantees

Enterprise SRE operations require strict safety. AURA ensures that no mutating operation is accidentally executed twice due to network retries or agent loops.

- **Idempotency Keys**: Every mutating tool call generates a unique idempotency key based on the tool name, arguments, and graph `thread_id`.
- **Postgres Tracking**: The key is stored in **Postgres**. If a network timeout causes the frontend to retry the resumption call, the backend checks Postgres.
- **Execution Locks**: Redis distributed locks prevent race conditions if concurrent approvals are fired. If an operation has already succeeded or is currently executing, the duplicate request is safely ignored, returning the cached result.

## Observability and Auditability

Transparency is critical for autonomous systems in production:

- **Execution Tracing**: Every step in the LangGraph execution, including LLM reasoning and tool outputs, is logged and traceable.
- **Audit Logs**: All mutating actions, approvals, and their outcomes are recorded in immutable audit logs for compliance and post-incident reviews.
