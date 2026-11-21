# AURA Project Handover

Snapshot taken 2026-11-20. Repo: `Muxie07/AURA`, branch `main`. No secrets are included here; all provider keys used during setup were rotated or revoked.

## 1. Architecture and stack

**Backend** (`backend/`, Python 3.12): FastAPI, async SQLAlchemy 2 + asyncpg, Alembic (migrations also run at app startup), pydantic-settings, structlog. Postgres 16 with pgvector; Redis for rate limiting, cost budgets and the ARQ job queue. Auth is JWT with RBAC roles (owner, admin, member, viewer) and multi-tenant organizations.

Main modules under `backend/app/`:
- `agents/`: planning, execution, verification, policies, memory, workflows
- `ai/`: provider abstraction (Google Gemini, OpenAI, Anthropic, an offline `heuristic` fallback, `mock`) and a model router
- `tools/`: tool registry and executor, built-in business tools, MCP and UTCP integrations (`mcp_main.py` is a separate MCP server)
- `rag/`, `knowledge/`: document ingestion, chunking, vector and full-text search
- `evaluation/`, `observability/`, `policy/`, `security/`, `worker.py` (ARQ worker)

**Frontend** (`frontend/`): Next.js 16, React 19, Tailwind 4, TypeScript. The Content Security Policy in `next.config.ts` derives its allowed API origin from `NEXT_PUBLIC_API_URL`.

**Infra files:** `docker-compose*.yml`, `.github/workflows/` (`ci.yml`, `deploy-backend.yml`, `security.yml`, `release.yml`), plus `ARCHITECTURE.md`, `DEPLOYMENT.md`, `DEMO.md`, `SECURITY.md`.

## 2. Implemented features

Judged from the API modules and frontend pages; not each one verified end to end.
- Login, conversations, agent runs with background execution, and a human-in-the-loop approvals flow with separation of duties (a requester can't approve their own run; only owner or admin roles can approve or reject).
- Agents, workflows, tools and MCP hub (list and ping servers), model providers API, knowledge base and RAG, evaluations, forecasting, audit logs, tenant invitations, Gmail integration, observability and settings.
- Frontend pages: agents, analytics, approvals, audit, conversations, evaluations, executions, knowledge, mcp, models, observability, settings, studio, tenants, tools, workflows, login.
- A demo organization and users are created by `backend/scripts/seed_data.py` (see that script and `DEMO.md` for the demo login).

Fixes made during this work: a missing migration (`schema_drift_fix`) for model columns that were never migrated, a repaired seed script, and an approval RBAC regression test file.

## 3. Git state

- Latest commit: `c5d4253` "test: create the pgvector extension before creating test tables".
- **Pushed:** yes. `HEAD` equals `origin/main`.
- Recent history, newest first: `c5d4253`, `1260d34`, `5ba8d16`, `b0620b0`, `5b08a86` (CSP fix), `3b7d758` (1 worker), `b52554a`, `2abda1d`, `d1e5793`.
- The branch `portfolio-cleanup` was fast-forward merged into `main` and deleted locally and on GitHub.

## 4. CI failure investigation

Three separate causes were found in sequence; each hid the next.

| # | Cause | Fix | Commit |
|---|---|---|---|
| 1 | `ci.yml` set `AURA_ENV=testing`, which the settings enum rejects. Pytest aborted at collection (exit code 2). | Use `development`. | `5ba8d16` |
| 2 | `test_mcp_hub_api` pinged `localhost:8000`. It passed locally only because the dev backend container listened there. | The HTTP client is faked in that test. | `1260d34` |
| 3 | A fresh pgvector database lacks the `vector` extension, so `create_all` failed on `document_chunks` and about 68 tests errored. | The `create_tables` fixture runs `CREATE EXTENSION IF NOT EXISTS vector` first. | `c5d4253` |

**Status after the last push (unresolved):** CI run `44782007615` for `c5d4253` has the `test` job stuck in the `Run Pytest` step, 37+ minutes at the time of writing. Containers (26s) and dependency install (20s) finished normally. The other jobs (`lint-and-typecheck`, `frontend-ci`, `security-scans`, `deploy`) passed.

**Not reproduced locally.** The exact CI command, in Linux, Python 3.12, against a brand-new `pgvector/pgvector:pg16` and `redis:7-alpine` on localhost with no `REDIS_HOST`, gives **196 passed, 3 skipped in about 39 seconds**. The slowest test was `test_boot` at 5.1s.

**Root cause of the hang: not confirmed.** I couldn't read the job log (no GitHub credentials, `gh` not installed, and the log API returns 403 anonymously), so the hanging test is unidentified. Leads, none proven:
- `tests/api/test_boot.py` loads `.env.example`, which sets `POSTGRES_HOST=postgres` and a `redis` host. Those names don't exist on a GitHub runner, so DNS behavior there may differ from Docker's.
- `app/security/rate_limit.py:17` creates a Redis client with no socket timeout (other call sites use 1–2s timeouts).
- App startup runs Alembic in a worker thread, guarded by an advisory lock in `migrations/env.py`, while tests hold open DB transactions.
- The `test` job has no `timeout-minutes`, so a stuck run lasts up to 6 hours.

A test of the DNS lead (run `test_boot` alone with an unreachable resolver) was attempted but **stalled during dependency install and never reached the test**, so it is inconclusive and the DNS lead is still untested.

**Suggested next step:** cancel the stuck run, then add `timeout-minutes` to the `test` job and run pytest with `-vv --durations=20 -o faulthandler_timeout=120`, so CI itself reveals the hanging test. Pushing that deploys the app, so it needs the owner's approval. Alternatively, read the full job log in the GitHub UI and search for the last test name.

Known, non-blocking debt: `ruff check` (about 128 errors) and `mypy` (about 169) fail but are `continue-on-error` in CI; `ruff format` passes and is blocking. Test output also shows a deprecation warning for `await redis_pool.close()`.

## 5. Working tree

- Tracked files: clean (no uncommitted changes).
- **70 untracked scratch files** in the repo root and `backend/` (`fix_*.py`, `patch_*.py`, `test_*.py`, logs, `openapi.json`, etc.). They are not committed and were there before this work. Do not commit them blindly.
- Running the test suite rewrites two tracked files, `backend/app/config/mcp_servers.json` and `tenant_invitations.json`; revert them with `git checkout --` after test runs. `backend/coverage.xml` is also generated.
- `HANDOFF.md` (contained credentials) was deleted. `AURA_HANDOVER.md` (this file) is new and uncommitted.
- Local machine: Docker Desktop is running, with the user's own AURA and Supabase containers. The temporary test containers (`ci-pg`, `ci-redis`, `ci-dns`) were removed; none remain.

## 6. Production deployment

| Part | Where | Notes |
|---|---|---|
| Frontend | Vercel project `aura-frontend`, `https://aura-frontend-teal.vercel.app` | Git integration connected, root directory `frontend`, production branch `main`. Auto-deploys on each push. |
| Backend | Render web service `aura-backend`, `https://aura-backend-z1qs.onrender.com` | Free plan, 512 MB, Docker build from `main`. |
| Database | Neon project `aura-demo` | Postgres 16, pgvector enabled, migrated to `schema_drift_fix`. |
| Redis | Upstash database `aura-demo-redis` | TLS. |

Backend deploys run from `.github/workflows/deploy-backend.yml`, which calls a Render deploy hook (stored as the GitHub secret `RENDER_DEPLOY_HOOK_URL`) on **every push to `main`**. Render's own auto-deploy flag is on but does nothing, because the Render GitHub app isn't installed on the repo.

Important constraints:
- **Cold starts:** the free backend sleeps after about 15 minutes idle; the first request takes 1–2 minutes.
- **Deploy downtime:** each backend deploy causes a few minutes of downtime, and every push to `main` triggers both a Render deploy and a Vercel rebuild.
- **Memory:** the Dockerfile defaults to 1 worker (`WEB_CONCURRENCY`) because 4 workers were OOM-killed at 512 MB.
- **CORS:** only `https://aura-frontend-teal.vercel.app` is allowed. Other Vercel aliases are protected or blocked.
- **LLM:** the models are set to `gemini-3.1-flash-lite` (via `FAST_MODEL`, `REASONING_MODEL`, `LONG_CONTEXT_MODEL`, `PRIMARY_LLM_MODEL`), because `gemini-3.8-flash` was overloaded at the time. Both `GEMINI_API_KEY` and `GOOGLE_AI_API_KEY` must hold the same key. The app silently falls back to the offline heuristic provider if Gemini fails, so check `provider` in `/api/v1/ai/generate` responses.
- **Embeddings are off:** `EMBEDDING_PROVIDER=ollama` was set only to pass production validation, and there is no Ollama server, so RAG embeddings don't work.
- **Production validation** (`settings.py`) requires non-default secrets that differ from each other, a JSON list in `AURA_TRUSTED_HOSTS` without wildcards or localhost, an `https` `AURA_API_BASE_URL`, JSON logging and a Google API key.
- **Credentials:** the two `AURA_*` secrets and the Gemini key were rotated; the Neon, Upstash, Render and Vercel access keys were revoked. There is currently **no automated access** to the Render or Vercel dashboards; changes there are manual. During the work, Render's API key could not read or write env vars (403), so they were edited in the dashboard, and **saving there does not redeploy**: use Manual Deploy or push a commit.

## 7. Unfinished tasks and decisions

**Open:**
1. Find and fix the hanging CI test (section 4); cancel run `44782007615`.
2. Clean up untracked scratch files and stray Docker containers.
3. Optionally switch the model variables back to `gemini-3.8-flash` when it is available.
4. Decide whether to restrict `deploy-backend.yml` to `backend/**` changes (currently every push redeploys).
5. Pay down ruff and mypy debt; add an embeddings provider if RAG is needed.

**Decisions made:**
- `main` was fast-forwarded and the working branch deleted.
- Tests build the schema with `create_all` (not Alembic), so the fixture now creates the pgvector extension.
- CI uses `AURA_ENV=development`.
- The Render deploy hook was chosen over installing the Render GitHub app.
