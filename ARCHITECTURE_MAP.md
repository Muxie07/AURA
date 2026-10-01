# AURA Architecture Map

## Overview
AURA is an Autonomous AI Business Operations Engineer.
- **Frontend**: Next.js (App router), React, Tailwind. Communicates via REST and SSE.
- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL (with pgvector), Redis.
- **AI/Agents**: LangGraph (or similar graph-based orchestration) for planning, execution, retrieval, and verification.
- **MCP Server**: Handles business logic tools (Customers, Products, Quotations).

## Key Layers
1. **API Layer (`backend/app/api/`)**: Route definitions, dependency injection (`Deps`), auth validation.
2. **Auth & Multitenancy**: `CurrentUserDep` extracts JWT, enforces tenant `organization_id` on all queries.
3. **Database (`backend/app/database/`)**: Async SQLAlchemy models (`User`, `Conversation`, `Message`, `AgentRun`, `AgentTraceEvent`).
4. **Agent Orchestration (`backend/app/agent/` or `backend/app/ai/`)**: The execution graph, tool calling, memory, streaming.
5. **Knowledge/RAG (`backend/app/knowledge/`)**: Document ingestion, chunking, vector search.
6. **Frontend (`frontend/src/app/`)**: Client-side fetching (`lib/api.ts`), Server-Sent Events for streaming agent runs.

## Identified Issues (Initial)
- **API 404 Handling**: Unhandled exceptions instead of graceful UI degradation.
- **Agent Timeout**: Hardcoded or missing timeouts in the LLM/Agent execution loop.
- **Natural Language**: Need fuzzy matching with human-in-the-loop disambiguation for destructive actions.
- **Security**: Need to verify `organization_id` is always used in WHERE clauses (IDOR check).
