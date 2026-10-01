# AURA Deployment

AURA is container-native and designed to be deployed onto Kubernetes or managed PaaS.

## Requirements
- PostgreSQL 15+ (with `pgvector` extension)
- Redis 7+
- Docker Engine

## Local Execution
```bash
docker-compose up -d --build
```
> Note: The environment currently runs PostgreSQL via Docker. Ensure Docker is running. If not, the application uses graceful fallbacks for local SQLite evaluation (falling back to keyword search instead of vector).

## Environment Configuration
Copy `.env.example` to `.env` and fill out your secrets.

- `AURA_SECRET_KEY`: Must be 32+ chars in prod.
- `AURA_ENV`: Set to `production` to activate strict validations.
- `OPENAI_API_KEY`: Required for LLM inference.
- `DATABASE_URL`: Connection string.

## Optimizations Enabled
- **Startup**: Database connection pre-ping, AsyncEngine pool scaling.
- **Query**: orjson JSON serialization for high-throughput Postgres IO.
- **RAG**: Reduced cross-encoder latency via asynchronous Cohere Reranking.
- **LLM**: Token-aware deterministic routing bypassing large models for simple parsing tasks.

## Migrations
Database migrations are automatically run during the backend container startup using Alembic. You can also run them manually:
```bash
docker compose exec backend alembic upgrade head
```

## Frontend Startup
The Next.js frontend is built as a standalone application in the Dockerfile. It runs on port 3000 by default and communicates with the backend via `NEXT_PUBLIC_API_URL`.
```bash
docker compose up -d frontend
```

## MCP Endpoint
The Model Context Protocol (MCP) server runs as a separate service for process isolation but shares the backend image. It listens internally on port 8000 and is accessible to the main backend at `http://mcp-server:8000/api/v1/mcp/`.

## Authentication
Authentication relies on JWT tokens. The `AURA_SECRET_KEY` must be securely generated. The system fetches the full user details from the database upon token validation to avoid relying on mock UUID identities in the token claims.

## Production Deployment
In production, ensure you use the `production` target for your Dockerfiles. Do not expose the MCP server or the PostgreSQL/Redis databases to the internet. Only the frontend (port 3000) and backend API (port 8000) should be placed behind a reverse proxy or load balancer. Set `AURA_ENV=production`.
