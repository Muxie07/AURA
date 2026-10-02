# AURA Architecture

AURA is an Autonomous AI Business Operations Engineer. It uses a Next.js frontend, a FastAPI async backend, PostgreSQL (with pgvector), Redis, and ARQ for background tasks.

## System Topology

```mermaid
flowchart TD
    subgraph Frontend
        UI[Next.js App UI]
        API_CLIENT[OpenAPI TypeScript Client]
    end

    subgraph Backend [FastAPI Backend]
        API_ROUTER[API Routers]
        MODEL_ROUTER[ModelRouter]
        POLICY_ENGINE[PolicyEngine]
        HITL[Approval/HITL]
        COST_MANAGER[CostManager]
        EVALS[Evaluators]
    end

    subgraph Workers [ARQ Worker Queue]
        AGENT_WORKER[Agent Workflow Service]
    end

    subgraph Data [Data Persistence & Cache]
        PG[(PostgreSQL + pgvector)]
        REDIS[(Redis)]
        RLS[Row-Level Security]
    end

    subgraph External [MCP & Integrations]
        MCP_SERVER[MCP Topology]
        LLM_PROVIDERS[Gemini / Claude / OpenAI]
    end

    UI -->|HTTP / SSE| API_ROUTER
    API_ROUTER --> MODEL_ROUTER
    API_ROUTER --> REDIS
    API_ROUTER --> PG
    
    API_ROUTER -->|Enqueue| AGENT_WORKER
    AGENT_WORKER --> MODEL_ROUTER
    AGENT_WORKER --> COST_MANAGER
    AGENT_WORKER --> POLICY_ENGINE
    AGENT_WORKER --> HITL
    
    POLICY_ENGINE --> MCP_SERVER
    POLICY_ENGINE --> EVALS
    
    MODEL_ROUTER --> LLM_PROVIDERS
    
    PG --> RLS
```

## Core Components
- **ModelRouter**: Handles transparent failovers, backoff jitter, and routing to Gemini/Claude/OpenAI.
- **PolicyEngine**: Authorizes tool executions and strictly applies risk levels (e.g. demanding approvals for WRITE/EXTERNAL).
- **Approval/HITL**: High-risk tool calls buffer here, binding to an args hash so approvals cannot be hijacked.
- **CostManager**: Limits token budgets securely using Redis atomic counters.
- **Evaluators**: Secondary LLM checkpoints validating groundedness (preventing RAG hallucinations) before responding to the user.
- **Worker Queue**: Background ARQ processors isolating long-running LLM loops from the HTTP interface.
- **MCP Topology**: A dedicated internal MCP server providing safe external tool bridging under strict organizational isolation.
