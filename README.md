# AURA — Autonomous SRE Agent

> **Enterprise-Grade Autonomous Site Reliability Engineering** powered by LangGraph, Claude, FastMCP, and a modern Next.js + FastAPI stack.

AURA is an intelligent, autonomous agent designed to investigate infrastructure incidents by chaining read-only diagnostic tools, reasoning over the evidence via RAG pipelines, and proposing safe remediations. All mutating actions are gated behind a strict Human-in-the-Loop (HITL) safety checkpoint, ensuring enterprise security and compliance.

---

## Features

- **Autonomous Investigation**: Intelligent chaining of diagnostic tools to troubleshoot failing services, network issues, and misconfigurations.
- **RAG-Powered Runbooks**: Automatically retrieves relevant runbooks and past incidents using PgVector to inform troubleshooting strategies.
- **Real-time Streaming (SSE)**: Streams agent thoughts, tool execution states, and terminal outputs to the frontend via Server-Sent Events.
- **Human-in-the-Loop (HITL)**: Read-only tasks run automatically. Any command that mutates state is paused for explicit human approval, guaranteeing safety.
- **Idempotent Execution**: Robust retry and state management powered by Postgres and Redis to prevent double-execution of destructive operations.
- **Multimodal Context**: Attach Grafana dashboards or terminal screenshots directly to the chat context for comprehensive incident analysis.
- **MCP Extensibility**: Built on the Model Context Protocol (MCP) to easily plug in new tools, diagnostics, and integrations across diverse infrastructure environments.
- **Multi-tenant Architecture**: Secure data isolation and tenant-specific configuration management.
- **Comprehensive Observability**: Deep tracing and logging of agent decision-making for auditability and continuous improvement.

---

## Architecture

AURA is engineered for high availability and enterprise scale. For a deep dive, see our [Architecture Documentation](./ARCHITECTURE.md).

**Core Components:**
- **Frontend**: Next.js 14 App Router, Tailwind CSS, providing a rich, terminal-like UI with real-time updates.
- **API Gateway & Orchestration**: FastAPI and LangGraph coordinate the complex, multi-step agent execution graph.
- **State & Idempotency**: PostgreSQL stores agent checkpoints, idempotency keys, and long-term memory.
- **Vector Search**: PgVector stores runbook embeddings and past incident resolutions for semantic retrieval.
- **Caching & Rate Limiting**: Redis ensures high-performance retrieval and mitigates runaway agent loops.
- **Real-time Comms**: SSE (Server-Sent Events) streams agent progress to the Next.js client.
- **Tool Execution**: FastMCP provides a standardized interface for interacting with secure diagnostic tools in isolated environments.

---

## Prerequisites

- **Docker & Docker Compose**: v2.20.0+
- **Node.js**: v20+ (if running frontend locally)
- **Python**: v3.11+ (if running backend locally)
- **Anthropic API Key**: For Claude access

---

## Quickstart

Get AURA up and running in minutes using our Docker Compose stack.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/AURA.git
cd AURA-FINAL

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY, Postgres credentials, etc.

# 3. Launch the full stack
docker compose up --build -d

# 4. View the dashboard
# Open http://localhost:3000 in your browser
```

For advanced deployments, custom tool integrations, and detailed API documentation, refer to the `/docs` directory.

---
*Built for production scale SRE operations.*
