# AURA — Phase 0 Audit Report

## 1. Modules
- **`app.api`**: Contains all FastAPI route definitions. Subdivided by domain (`agents`, `eval`, `conversations`, `knowledge-bases`).
- **`app.agents`**: The core graph engine, planner, verifier, and execution logic.
- **`app.ai`**: LLM integrations (Gemini, OpenAI, Mock, Heuristic), router, and struct generation logic.
- **`app.config`**: Environment settings (pydantic-settings).
- **`app.core`**: Exception handling and dependencies.
- **`app.database`**: SQLAlchemy models and setup.
- **`app.evaluation`**: Dataset execution and metrics logic.
- **`app.knowledge`**: RAG logic (storage, chunking, retrieval, generation).
- **`app.memory`**: Conversation state persistence.
- **`app.observability`**: Tracing, logs, and metrics middleware.
- **`app.policy`**: Execution policies and guards.
- **`app.security`**: Rate limiters and future RBAC/auth handlers.
- **`app.tools`**: Business tools (pricing, quotes, customers) and MCP client integration.

## 2. API Endpoints (Current Status)

| Path | Method | Auth Dependency | Org Derived From | RBAC Role Required | Risk |
|---|---|---|---|---|---|
| `/api/v1/agent/runs` | POST | `get_current_user` | Request Body / None (VULN) | None | High |
| `/api/v1/agent/runs/{id}` | GET | `get_current_user` | None (VULN) | None | Medium |
| `/api/v1/agent/runs/{id}/stream` | GET | `get_current_user` | None (VULN) | None | Medium |
| `/api/v1/agent/approvals/{id}` | POST | `get_current_user` | None (VULN) | None | High |
| `/api/v1/agent/approvals` | GET | `get_current_user` | None (VULN) | None | Medium |
| `/api/v1/conversations` | GET | `get_current_user` | JWT (via context) | None | Low |
| `/api/v1/knowledge-bases` | POST/GET | `get_current_user` | JWT (via context) | None | Medium |
| `/api/v1/eval/datasets` | POST/GET | `get_current_user` | None (VULN) | None | High |
| `/api/v1/eval/benchmarks` | GET | `get_current_user` | None (VULN) | None | Low |
| `/api/v1/auth/token` | POST | None | N/A | N/A | High |
| `/health` | GET | None | N/A | N/A | Low |
| `/ready` | GET | None | N/A | N/A | Low |

*(Note: "None (VULN)" indicates that the endpoint does not strictly enforce tenant isolation by extracting the Org ID from the JWT token natively at the route/DB layer, making it susceptible to IDOR.)*

## 3. Frontend Pages
- `/`: Dashboard
- `/agents`: Agent overview
- `/approvals`: Pending run approvals
- `/conversations`: Chat interface
- `/evaluations`: Evals and datasets
- `/knowledge`: KB management
- `/login`: Auth portal

## 4. Risks Identified
- **Tenant Scope / IDOR**: Most API routes accept IDs directly without asserting they belong to the `organization_id` defined in the JWT. 
- **Row-Level Security**: No database-level row isolation.
- **RBAC**: No strict hierarchical Role-Based Access Control logic on administrative endpoints.
- **Agent Sandbox**: Timeout and resource leak risks if the agent graph gets trapped in a replan loop.
