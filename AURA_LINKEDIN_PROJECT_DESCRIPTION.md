# Project: AURA (Autonomous Site Reliability Engineering Agent)

**Role**: Lead AI/Backend Engineer

## 🚀 The Problem
Modern infrastructure is complex. When a critical service degrades at 3 AM, on-call engineers spend valuable time context-switching between monitoring dashboards, terminal sessions, and fragmented runbooks. Existing automation tools require rigid, pre-defined scripts that break when environments change, while naive LLM tools lack the context and safety guardrails required for production environments.

## 💡 The Solution: AURA
I architected and developed AURA, an enterprise-grade autonomous SRE agent that acts as an intelligent force multiplier for DevOps teams. AURA automatically investigates incidents, reasons over complex system states, and proposes concrete remediations, safely executed via a Human-in-the-Loop (HITL) checkpoint.

## 🏗️ Architecture & Core Technologies
AURA is built on a modern, highly scalable stack designed for production resilience:
- **Orchestration**: Built the reasoning engine using **LangGraph** and **Claude**, implementing a cyclical graph for tool execution and decision-making.
- **Backend & Streaming**: Developed a **FastAPI** gateway that streams real-time agent thoughts and tool outputs to a **Next.js 14** frontend via Server-Sent Events (SSE).
- **Data & State Management**: Utilized **PostgreSQL** for checkpointing graph state and **Redis** for distributed locking and caching.

## 🧠 Key Engineering Contributions

- **RAG-Powered Runbooks**: Engineered a Retrieval-Augmented Generation pipeline using **PgVector**. AURA semantically searches past incidents, architectural docs, and standard operating procedures to ground its reasoning in the organization's specific context.
- **Human-in-the-Loop (HITL) Safety**: Implemented strict safety boundaries. Read-only diagnostic tools run autonomously, but any state-mutating action triggers a LangGraph interrupt, pausing execution until explicit human approval is received via the UI.
- **Idempotency Guarantees**: Solved the critical issue of double-execution in distributed systems. Designed an idempotency engine using Postgres state tracking and Redis distributed locks to ensure that network retries or duplicate approvals never result in unsafe, repeated operations.
- **Extensible Tooling via MCP**: Integrated the **Model Context Protocol (MCP)** (via FastMCP), allowing AURA to securely interface with diverse external systems (AWS, Kubernetes, Datadog) without hardcoding fragile integrations into the core agent.
- **Multi-Tenancy & Observability**: Architected the system for multi-tenant SaaS deployment, ensuring strict data isolation at the database layer. Implemented deep execution tracing and immutable audit logging for every LLM decision and tool execution, providing out-of-the-box compliance and post-mortem artifacts.

## 📈 Impact
AURA transforms incident response by reducing Mean Time to Resolution (MTTR) and minimizing human fatigue. By combining the adaptive reasoning of Large Language Models with the strict safety constraints of traditional engineering, AURA proves that autonomous agents can be safely deployed in high-stakes enterprise environments.
