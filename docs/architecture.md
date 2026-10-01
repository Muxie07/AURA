# AURA Architecture

This document describes the high-level architecture of AURA — Autonomous AI Business Operations Engineer.

## System Overview

```mermaid
graph TB
    subgraph Client["Client Layer"]
        FE["Next.js Frontend"]
        CLI["CLI / API Clients"]
    end

    subgraph API["API Layer (FastAPI)"]
        GW["API Gateway<br>/api/v1"]
        MW["Middleware<br>(RequestID, CORS, Auth)"]
        EH["Exception Handlers"]
    end

    subgraph Agent["Agent Layer (LangGraph)"]
        IA["Intent Analyzer"]
        PL["Planner"]
        TE["Tool Executor"]
        VA["Result Validator"]
        HITL["Human-in-the-Loop<br>Approval Gate"]
    end

    subgraph Tools["Tool Registry"]
        TL1["Customer Lookup"]
        TL2["Product Lookup"]
        TL3["Pricing Engine"]
        TL4["Quotation Generator"]
        TL5["CRM Updater"]
        TL6["Email Simulator"]
    end

    subgraph AI["AI Layer"]
        LLM["LLM Provider<br>Abstraction"]
        EMB["Embedding<br>Provider"]
    end

    subgraph RAG["RAG Pipeline"]
        ING["Document Ingestion"]
        CHK["Chunker"]
        VEC["Vector Store<br>(pgvector)"]
        RET["Retriever + Reranker"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL<br>+ pgvector")]
        RD[("Redis<br>Cache / Queue")]
    end

    subgraph Obs["Observability"]
        LOG["Structured Logging<br>(structlog)"]
        TRC["Agent Traces"]
        AUD["Audit Events"]
    end

    FE --> GW
    CLI --> GW
    GW --> MW
    MW --> EH
    MW --> Agent

    Agent --> IA
    IA --> PL
    PL --> TE
    TE --> VA
    VA --> HITL
    HITL --> TE

    TE --> Tools
    IA --> LLM
    PL --> LLM
    VA --> LLM

    LLM --> AI
    EMB --> AI

    ING --> CHK
    CHK --> VEC
    VEC --> PG
    RET --> VEC

    Agent --> Obs
    API --> Obs
    Obs --> PG
    Agent --> Data
    Tools --> Data
```

## Component Responsibilities

### API Layer
The FastAPI application serves as the entry point for all external interactions.
Key responsibilities:
- Request validation (Pydantic)
- Authentication / authorization (Phase 7)
- Request ID assignment and propagation
- Routing to domain handlers
- Structured error responses

### Agent Layer
The agent orchestrates multi-step business workflows through a controlled state machine.
Key design decisions:
- **Explicit state transitions** — no hidden autonomous loops
- **Maximum iteration cap** — prevents runaway agents
- **Hard timeout** — guarantees bounded execution time
- **Human-in-the-loop gate** — high-impact actions require approval
- **Full execution trace** — every decision is recorded

### Tool Registry
Tools are the agent's actuators — the only way it can affect the outside world.
Each tool has:
- Explicit input/output schema
- Permission requirements
- Timeout configuration
- Mock/real adapter separation

### RAG Pipeline
Retrieval-Augmented Generation for enterprise knowledge.
- Document ingestion with metadata
- Semantic chunking with overlap
- pgvector similarity search
- Reranking for precision
- Source attribution on every answer

### Data Layer
PostgreSQL is the single source of truth.
- All agent runs, traces, and audit events persist here
- pgvector stores embeddings in the same database
- Redis handles ephemeral state (rate limiting, session cache, task queues)

## Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant MW as Middleware
    participant AG as Agent
    participant TL as Tool
    participant DB as Database

    U->>API: POST /api/v1/agent/run
    API->>MW: Assign Request ID
    MW->>AG: Start AgentRun
    AG->>DB: INSERT agent_run (PENDING)
    AG->>AG: Analyze Intent
    AG->>AG: Plan Steps
    loop Tool Execution
        AG->>TL: Execute Tool
        TL-->>AG: Result
        AG->>DB: INSERT tool_call
    end
    AG->>AG: Validate Result
    AG->>DB: UPDATE agent_run (COMPLETED)
    AG-->>API: Final Response
    API-->>U: 200 + Trace
```

## Database Schema (Phase 1)

```mermaid
erDiagram
    organizations ||--o{ users : "has"
    organizations ||--o{ conversations : "owns"
    users ||--o{ conversations : "creates"
    conversations ||--o{ messages : "contains"
    conversations ||--o{ agent_runs : "triggers"
    agent_runs ||--o{ messages : "produces"
    agent_runs ||--o{ tool_calls : "makes"
    agent_runs ||--o{ approval_requests : "requires"
    agent_runs ||--o{ audit_events : "generates"
    tool_calls }o--o| approval_requests : "awaits"
```

## Security Model

```
┌─────────────────────────────────────────────────────┐
│                  Trust Boundary                      │
│                                                      │
│  User Input ──► Validation ──► Agent                │
│                                                      │
│  Retrieved Docs ──► [UNTRUSTED] ──► Context Window  │
│  Tool Outputs   ──► [UNTRUSTED] ──► Agent           │
│                                                      │
│  Agent can only act through Tool Registry           │
│  Tool Registry enforces permissions                 │
│  High-impact tools require human approval           │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Technology Decisions

See `docs/decisions/` for detailed Architecture Decision Records (ADRs).
