# AURA: Autonomous Enterprise AI Business Operations Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.0-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.2-dc382d.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AURA** (Autonomous Unified Reasoning Architecture) is an enterprise-grade, deterministic AI operations platform designed to execute complex business workflows with strict security boundaries, human-in-the-loop (HITL) governance, multi-tenant isolation, and auditable tool execution.

---

## 🌟 Key Capabilities

### 1. Human-in-the-Loop (HITL) Governance & Risk Tiering
- **Granular Action Classification:** Tools are categorised by risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Cryptographic Approval Links:** High-risk actions (e.g., executing payments, issuing invoices, emailing external clients) pause execution and trigger one-click cryptographic email approval requests.
- **Approval Inbox & Audit Trail:** Interactive inbox with real-time SSE streaming for pending approvals, detailed decision rationale, parameter inspection, and immutable audit logs.

### 2. Dual-Channel Email & Gmail Integration
- **Google OAuth 2.0 Integration:** Secure OAuth flow with automatic token refreshes, encrypted token storage via Fernet symmetric encryption, and multi-tenant credential isolation.
- **App Password (SMTP) Gateway:** Direct fallback support for corporate SMTP gateways (Gmail, Microsoft 365, internal SMTP relay).
- **Automated Notifications:** Formatted HTML action proposals with direct secure Approve/Deny endpoints.

### 3. Agent Execution Engine & Real-Time Traceability
- **Deterministic State Graphs:** Built on LangGraph stateful execution nodes (Plan, Act, Re-plan, Verify).
- **Live Streamed Execution:** Server-Sent Events (SSE) stream step-by-step agent reasoning, tool execution status, parameters, and live status to the frontend.
- **Fail-Safe Fallbacks:** Robust error recovery with automatic fallback to heuristic/mock engines if primary LLM quotas or connectivity fail.

### 4. Dynamic Tool Registry, MCP & UTCP
- **Model Context Protocol (MCP):** Connect to external tool servers via standard JSON-RPC over HTTP or stdio.
- **Universal Tool Calling Protocol (UTCP):** Dynamic runtime schema translation, parameter type validation, and cryptographic argument binding.
- **Built-in Business Suite:** Tools for commercial knowledge base retrieval, customer management, quotation calculations, and PDF invoice generation.

### 5. Multi-Tenant Enterprise Isolation
- **Row-Level Security:** Strict organization boundaries enforced via UUID foreign keys on all data models.
- **Tenant Management:** Multi-tenant workspace invitations, role-based access control (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`), and isolated configurations.

### 6. Financial Intelligence & Model Evaluation
- **Budget Guarantees:** Dynamic cost tracking, latency monitoring, and token budgeting per model and tenant.
- **Benchmarking Suite:** Integrated evaluation engine measuring precision, recall, latency, and cost across custom model runs.

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    subgraph Client ["Frontend (Next.js 16 + React 19)"]
        UI[Enterprise Web Dashboard]
        SSE[SSE Live Execution Monitor]
        ApprovalUI[HITL Approval Inbox]
    end

    subgraph Gateway ["API Gateway (FastAPI 0.115)"]
        Auth[JWT / RBAC Middleware]
        RateLimit[Rate Limiter & Tenant Context]
        Router[API v1 Routers]
    end

    subgraph AgentRuntime ["AURA Agent Runtime (LangGraph)"]
        Planner[Planning & Strategy Engine]
        Decision[Risk Classifier & Policy Engine]
        ToolReg[Tool Registry & UTCP Manager]
        MCPHub[Distributed MCP Hub]
    end

    subgraph Services ["External & Storage Services"]
        PG[(PostgreSQL 16 + pgvector)]
        RD[(Redis Cache & ARQ Queue)]
        GMail[Gmail OAuth / SMTP Service]
        LLM[LLM Providers (OpenAI, Gemini, Claude)]
    end

    UI -->|REST / JSON| Gateway
    SSE -->|EventStream| Gateway
    ApprovalUI -->|Approve/Deny| Gateway

    Gateway --> Router
    Router --> AgentRuntime
    Decision -->|Requires Approval| GMail
    ToolReg --> MCPHub
    AgentRuntime --> PG
    AgentRuntime --> RD
    AgentRuntime --> LLM
```

---

## 💻 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, ARQ, AsyncPG |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons, jsPDF |
| **Datastores** | PostgreSQL 16 (with `pgvector` for semantic search), Redis 7.2 |
| **AI Orchestration** | LangGraph, LangChain, Custom Heuristic Engine, OpenAI, Google Gemini, Anthropic |
| **Tooling & Standards**| Model Context Protocol (MCP), Universal Tool Calling Protocol (UTCP), OpenAPI 3.1 |
| **DevOps & QA** | Docker Compose, Pytest, Pytest-Asyncio, Ruff, ESLint |

---

## 📁 Repository Structure

```text
AURA-FINAL/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph state machine, nodes, and planning engine
│   │   ├── ai/              # Multi-provider LLM integrations (Google, OpenAI, Heuristic)
│   │   ├── api/             # FastAPI REST endpoints and v1 routes
│   │   ├── config/          # App settings, environment schema, and seed configurations
│   │   ├── database/        # SQLAlchemy 2.0 async models and session factories
│   │   ├── evaluation/      # LLM evaluation engine, cost tracking, and metrics
│   │   ├── knowledge/       # RAG pipeline, document ingestion, and vector embeddings
│   │   ├── observability/   # Structured logging, timing middleware, and error handlers
│   │   ├── security/        # Cryptographic vault and credential encryption
│   │   ├── services/        # Gmail OAuth, SMTP sending, and email notification services
│   │   └── tools/           # Dynamic Tool Registry, UTCP engine, and MCP client/server
│   ├── migrations/          # Alembic database migrations
│   ├── scripts/             # Database seed scripts and demo utilities
│   └── tests/               # Pytest suite (190+ unit and integration tests)
├── frontend/
│   ├── src/app/
│   │   ├── agents/          # Agent management and configuration
│   │   ├── analytics/       # System metrics and usage analytics
│   │   ├── approvals/       # HITL approval inbox and audit reviews
│   │   ├── audit/           # Immutable compliance and tool execution logs
│   │   ├── conversations/   # Real-time chat interface with SSE reasoning stream
│   │   ├── evaluations/     # Benchmarking runs and model comparisons
│   │   ├── executions/      # End-to-end execution traceability details
│   │   ├── knowledge/       # Knowledge base and document management
│   │   ├── mcp/             # MCP Hub server management
│   │   ├── models/          # LLM provider configuration and token budget tracking
│   │   ├── settings/        # System configuration and Gmail OAuth/SMTP management
│   │   ├── tenants/         # Multi-tenant workspace administration
│   │   └── workflows/       # Visual workflow DAG builder and executor
│   └── public/              # Static assets
├── docker-compose.yml       # Production/staging container orchestration
├── .env.example             # Complete environment configuration template
└── README.md                # Platform documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Docker Desktop** (version 24+ recommended)
- **Node.js** (v20+ LTS)
- **Python** (v3.12+)

### 2. Environment Configuration
Clone the repository and create your local `.env` file from the provided template:

```bash
cp .env.example .env
```

Edit `.env` to configure your API keys and parameters:
```dotenv
# Backend Configuration
AURA_SECRET_KEY=your-32-char-cryptographic-secret
DATABASE_URL=postgresql+asyncpg://aura_user:aura_dev_password@localhost:5432/aura_db
REDIS_URL=redis://localhost:6379/0

# LLM Providers (Configure at least one)
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-...

# Google OAuth & Gmail (Optional, for email approvals)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/gmail/oauth/callback
```

### 3. Start with Docker Compose
Run the entire platform including PostgreSQL (with pgvector), Redis, Backend, and Frontend:

```bash
# Build and spin up all containers
docker compose up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head

# Seed initial enterprise data (tenants, agents, MCP tools)
docker compose exec backend python scripts/seed_data.py
```

### 4. Running Locally for Development

#### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

The application will be accessible at:
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Interactive OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 🧪 Testing & Verification

AURA is rigorously tested with over 190 automated tests covering unit logic, database migrations, API contracts, and end-to-end agent workflows.

### Run Backend Test Suite
```bash
cd backend
pytest -v
```

### Run Frontend Linting & Build Verification
```bash
cd frontend
npm run lint
npm run build
```

### Code Formatting & Quality
```bash
# Backend lint and format
cd backend
ruff check .
ruff format --check .
```

---

## 🔒 Security & Governance

- **Zero-Trust Tool Execution:** All tools require authorization and argument schema validation via UTCP prior to execution.
- **Credential Storage:** Secrets, tokens, and OAuth keys are encrypted at rest using AES-128-CBC / Fernet keys.
- **Audit Logging:** Every state transition, LLM decision, and tool invocation is recorded with structured context variables (`trace_id`, `org_id`, `user_id`).
- **Secret Scanning Guardrails:** Pre-commit rules and `.gitignore` configurations prevent accidental credential leakage.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
