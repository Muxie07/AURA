# Phase 6 Design: AURA Intelligent Agent + Production Reliability

## 1. Intelligent Model Router
- **Directory**: `app/ai/routing/`
- **Concept**: Before executing a prompt, a task is classified by type (e.g., `SIMPLE_CLASSIFICATION`, `COMPLEX_REASONING`, `TOOL_USE`). Based on the `TaskProfile` and available model configurations, the router selects the best model for the job (balancing capabilities, context length, cost, latency) and returns a `ModelSelection`.
- **Implementation**: 
  - `TaskProfile` (Pydantic model)
  - `ModelSelection` (Pydantic model)
  - `ModelRouter` class that takes a prompt and context, classifies the task (using a fast model or heuristics), and selects the primary and fallback models from configuration.

## 2. Model Fallback
- **Concept**: If an LLM call fails due to timeout, rate limit, or provider error, the system must gracefully fall back to alternative models.
- **Implementation**: Wrap LLM execution in a retry/fallback decorator or logic inside `LLMService` that consults the `ModelRouter`'s fallback list.

## 3. Self-Correcting Agent & Failure Diagnosis
- **Directory**: `app/agents/` and `app/agents/verification/`
- **Concept**: Instead of a simple linear execution, the agent loops: `EXECUTE -> VERIFY -> (if fail) DIAGNOSE -> REPLAN -> EXECUTE`.
- **Implementation**:
  - Add `DIAGNOSE` and `REPLAN` nodes to the `WorkflowGraph`.
  - Configurable limits: `MAX_REPLAN_ATTEMPTS`, `MAX_TOOL_CALLS`, `MAX_AGENT_RUNTIME`.
  - `FailureDiagnosis` model that categorizes failures (`VALIDATION_ERROR`, `TOOL_ERROR`, etc.) and recommends an action (`RETRY`, `REPLAN`, `ASK_USER`, `FAIL`).

## 4. Enterprise Policy Engine & Approvals
- **Directory**: `app/policy/`
- **Concept**: Before any tool executes, a deterministic `PolicyEngine` evaluates the action.
- **Implementation**:
  - `PolicyRule` mapping tool risk levels and names to required permissions.
  - Returns `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`.
  - If `REQUIRE_APPROVAL`, the tool execution pauses, creating an `ApprovalRequest` in the DB. The agent run is suspended (status `AWAITING_APPROVAL`) until approved via API.

## 5. Agent Observability, Tokens & Latency
- **Directory**: `app/observability/`
- **Concept**: Every step of the agent's execution is tracked deterministically.
- **Implementation**:
  - Update `AgentRun` model to include tokens, cost, and latency.
  - Create `AgentTraceEvent` model (DB table) to store granular events (`RUN_STARTED`, `TOOL_SELECTED`, etc.).
  - Centralized cost calculator based on input/output tokens.

## 6. Prompt Injection Defense & Output Validation
- **Concept**: Clear boundaries between instructions and data.
- **Implementation**: Ensure user queries and RAG context are injected securely, avoiding system prompt leakage. Validate all tool/structured outputs through Pydantic.

## 7. Frontend Agent Dashboard & UI
- **Directory**: `frontend/app/agent/`
- **Concept**: Professional dashboard to monitor runs, view traces, and approve actions.
- **Implementation**:
  - `page.tsx` for dashboard overview.
  - `runs/[id]/page.tsx` for detailed timeline.
  - `approvals/page.tsx` for pending approval management.

## 8. Database & API
- **Migrations**: New tables for `agent_trace_events` and `approval_requests`.
- **API Endpoints**: 
  - `GET /api/v1/agent/runs`
  - `GET /api/v1/agent/runs/{id}/trace`
  - `POST /api/v1/approvals/{id}/approve|reject`

## Execution Plan
1. **Core Models**: Define the Pydantic schemas and SQLAlchemy models for trace events, approvals, and updated runs. Create Alembic migration.
2. **AI Layer**: Implement `ModelRouter` and fallback logic in `LLMService`.
3. **Policy Engine**: Implement the deterministic policy evaluator and approval flow.
4. **Agent State Machine**: Update `WorkflowGraph` with Diagnose/Replan loops and bounded limits.
5. **Observability**: Wire up event recording across the agent lifecycle.
6. **API & Tests**: Build the REST endpoints and write comprehensive unit/integration tests.
7. **Frontend**: Build the React dashboards.
8. **Security Audit & Final Polish**.
