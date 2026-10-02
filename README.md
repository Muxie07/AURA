# AURA: Autonomous AI Business Operations Engineer

AURA is an enterprise-grade, deterministic AI agent system that acts as a secure, autonomous business operations engineer. Built entirely on a robust modern stack with Python, FastAPI, React/Next.js, and PostgreSQL.

## Features
- **Strict Role-Based Access Control (RBAC)** and isolated Multi-Tenancy (Row-Level Security).
- **Idempotency** guarantees and atomic background job processing via ARQ.
- **Model Context Protocol (MCP)** compatible tool executions with cryptographic arg-binding and Human-in-the-Loop approvals.
- **Grounded RAG Pipeline** preventing hallucinations.
- **Circuit Breakers and Cost Controls** ensuring budget guarantees.
- **Enterprise Observability** out-of-the-box (Structlog contextvars, metrics, OTel stubs).

## Quickstart

### Prerequisites
- Docker Engine / Docker Desktop (Windows/WSL/macOS/Linux)
- Python 3.12+ (for local tooling)
- Node.js 20+

### Setup
1. Clone the repository and configure your environment:
   ```bash
   cp .env.example .env
   # Add your Gemini or OpenAI API keys in .env
   ```
2. Build and start the infrastructure:
   ```bash
   docker compose build
   docker compose up -d
   ```
3. Initialize the database and seed the demo dataset:
   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python scripts/seed_data.py
   ```
4. Access the platforms:
   - Frontend: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`

## Documentation
- [Architecture](ARCHITECTURE.md)
- [Security Threat Model](SECURITY.md)
- [Runbook](backend/docs/RUNBOOK.md)
- [Contributing](CONTRIBUTING.md)

## License
MIT License. See [LICENSE](LICENSE) for details.
