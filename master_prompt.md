<USER_REQUEST>
# AURA — MASTER UPGRADE PROMPT (paste this whole file into Antigravity)

> **How to use:** Paste everything below into Antigravity once. It is built as a phase-gated plan: the agent must finish one phase, report, and **stop** until you reply `continue`. This keeps each step reviewable and avoids burning your quota on one giant unreviewable change.
>
> **Do these yourself BEFORE pasting (the agent cannot do them):**
> 1. **Rotate your Google AI key.** Your local `.env` contains a real-looking `GOOGLE_AI_API_KEY`. It has passed through several tools and chats. Revoke it in Google AI Studio and create a new one. Never paste `.env` into any chat again.
> 2. `git init` / commit your current state to a branch called `pre-hardening` so everything is reversible.
> 3. Generate real secrets: `python -c "import secrets; print(secrets.token_urlsafe(48))"` for `AURA_SECRET_KEY` and again for `AURA_INTERNAL_API_KEY`.

---

## ROLE AND MISSION

You are a principal engineer, security architect and SRE hardening **AURA — Enterprise AI Agent Platform** into a production-grade, multi-tenant, auditable system comparable to leading enterprise agent platforms.

Stack: FastAPI (async) + SQLAlchemy 2 async + asyncpg + PostgreSQL/pgvector + Alembic + Redis + Next.js frontend + MCP (client and server) + Docker Compose. Primary LLM provider in use: **Google Gemini** (`backend/app/ai/providers/google.py`), with OpenAI/Anthropic/Mock/Heuristic providers also supported.

Core pipeline: User → Next.js → FastAPI gateway (JWT, RBAC, tenant isolation, validation, rate limit, request logging) → Agent engine (normalize → intent → plan → RAG → tool select → execute → verify → respond) → LLM provider + Knowledge/RAG + Business tools → Business systems. Also present: ModelRouter, PolicyEngine (READ/WRITE/EXTERNAL risk classes), human approval, CostManager, evaluators, ToolExecutionAudit, AgentTraceEvent.

Goal: **correct, secure, tenant-isolated, observable, reproducible, tested, deployable.** Quality over speed. Do not claim something works unless you ran it and saw it pass.

## WORKING RULES (non-negotiable)

1. **Phase gates.** Work on exactly one phase at a time. At the end of each phase output: (a) summary, (b) files changed, (c) exact commands you ran with real results, (d) what remains risky, (e) the question "Continue to Phase N+1?" Then **stop**.
2. **Create a git branch per phase** (`hardening/p0-hygiene`, `hardening/p1-startup`, …). Small, atomic commits with clear messages. Never force-push, never rewrite history, never `--no-verify`.
3. **Edit source files directly.** Do NOT write regex/string-replace patch scripts (`fix_*.py`, `update_*.py`, `append_*.py`). Those caused broken syntax, non-idempotent edits and duplicated code in this repo.
4. **Never open, print, log or commit `.env` or any secret.** Only touch `.env.example` and docs.
5. **Never edit an already-applied Alembic migration.** Add new migrations. Every schema change needs `upgrade()` and a working `downgrade()`.
6. **Baseline first.** Before changing anything run the existing test suite and `ruff check` and record results in `docs/BASELINE.md`. After each phase tests must be ≥ baseline and ruff must not regress.
7. **Verify, don't assume.** Several files were not reviewed by me (agent engine, tools, registry, executor, policy, RAG, providers, API routes, frontend). For every item below that touches them, **read the current code first**, confirm the problem exists, then fix. If an item does not apply, say so and skip it.
8. **Fail closed.** Any ambiguity in auth, tenancy, approval or policy must deny, not allow.
9. **No placeholder code**, no `TODO: implement`, no swallowed exceptions (`except Exception: pass`). Log or re-raise with `raise ... from err`.
10. Python 3.12+, full type hints, structured logging via the existing `get_logger`, async everywhere on I/O.
11. Keep public API paths backward compatible unless a change is listed here. If you must break something, document it in `CHANGELOG.md`.

---

# PHASE 0 — Audit, safety net, repo hygiene

**0.1 Read-only audit.** Produce `docs/AUDIT.md` covering every backend module, route, tool, node, model and frontend page: purpose, auth requirement, tenant scoping (yes/no/how), risk. Include a table of **every API endpoint** with columns: path, method, auth dependency, org derived from (JWT / request body / none), RBAC role required. This table drives Phase 2.

**0.2 Baseline.** Run backend tests, `ruff check`, `mypy` (report only), frontend lint/build. Record in `docs/BASELINE.md`. (Existing tests live in `backend/tests/{agent,knowledge,tools/mcp}` and `test_phase9_eval.py`. Keep them; they are an asset.)

**0.3 Delete throwaway scripts** after confirming their changes are already present in the real source files (diff against intent). Candidates: `fix_eval_auth.py`, `fix_eval_auth_syntax.py`, `fix_eval_auth_syntax2.py`, `append_models.py`, `fix_exec.py`, `fix_migration.py`, `update_agent_routes.py`, `update_agent_service.py`, `update_docker.py`, `update_main.py`, `backend/fix.py`, `backend/generate_tests.py`, `backend/update_models.py`. If any intended change is NOT in the source, apply it properly in the relevant later phase rather than running the script.

**0.4 `.gitignore` bug.** The Python section ignores `lib/` and `lib64/`, which will silently exclude Next.js `src/lib/` (utils, api client) from git. Change to root-anchored `/lib/`, `/lib64/`, `/backend/lib/` etc. Also add `.env*` allow-rule so `.env.example` stays tracked: `!.env.example`. Verify with `git check-ignore -v frontend/src/lib/anything.ts`.

**0.5 Line endings (you are on Windows).** Several files have CRLF endings (`models.py`, `.env`). CRLF breaks bash scripts (`$'\r': command not found`) and can leak `\r` into env values. Add `.gitattributes`:
```
* text=auto eol=lf
*.sh text eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
*.png binary
```
Run `git add --renormalize .`. Add `.editorconfig` (LF, utf-8, 4 spaces python / 2 spaces ts).

**0.6 `.dockerignore`** (backend and frontend): exclude `.env*`, `.git`, `tests/` (prod image), `__pycache__`, `.venv`, `node_modules`, `.next`, `*.md` except README, `docs/`, `evaluation/reports`. Currently the production stage does `COPY . .` which would bake `.env` into the image if present.

**0.7 Ruff to zero.** `ruff_all.txt` (it is UTF-16 encoded; regenerate with `ruff check . --output-format=full > ruff_all.txt` in UTF-8) reports **106 errors**. Fix properly, not by blanket ignoring:
- `ARG002/ARG005/ARG004` (≈38): unused `**kwargs`/args in node `_execute` overrides and lambdas in `builtin_nodes.py`, `agent_service.py`, `evaluation/engine.py`. If the base-class signature requires them, rename to `_kwargs` or add targeted `per-file-ignores`; otherwise remove.
- `B904` (7): `raise ... from err` in `ai/providers/google.py:165`, `api/deps.py:63,80`, `main.py:74`, `tools/executor.py:51,57`, `tools/mcp/client.py:43`.
- `E402` in `api/deps.py:44-48`: move imports to top (check for circular import first; if circular, fix the design, don't hide it).
- `F401` incl. `tools/mcp/client.py` importing **`httpx2`** — that is not a standard package. Determine why it is there. Possible typo or **typosquat risk**. Remove or replace with `httpx`, and check `pyproject.toml`/lockfile for it.
- `RUF012` (mutable class defaults → `ClassVar`/`field(default_factory=…)`), `B017` (`pytest.raises(Exception)` → specific exception), `F841`, `SIM102/105/108`, `UP017`, `PTH123/103`, `W293`, `I001`.
Result: `ruff check .` and `ruff format --check .` clean.

**Acceptance:** AUDIT.md + BASELINE.md exist; git clean; throwaway scripts gone; ruff = 0; tests ≥ baseline.

---

# PHASE 1 — Configuration, startup, migrations, containers

### 1.1 `settings.py` / `.env.example` — real bugs found

- **Env var name mismatch (silent misconfiguration).** `.env.example` and the user's `.env` use `MODEL_PROVIDER` / `MODEL_NAME`, but `Settings` reads `primary_llm_provider` / `primary_llm_model` (env `PRIMARY_LLM_PROVIDER` / `PRIMARY_LLM_MODEL`). Because of `extra="ignore"`, `MODEL_PROVIDER=google` is **ignored** and the app silently falls back to OpenAI/gpt-4o with no key. Fix with aliases and update `.env.example`:
```python
from pydantic import AliasChoices
primary_llm_provider: ModelProvider = Field(
    default=ModelProvider.GOOGLE,
    validation_alias=AliasChoices("PRIMARY_LLM_PROVIDER", "MODEL_PROVIDER"),
)
primary_llm_model: str = Field(
    default="gemini-2.5-flash",  # confirm current model ids against Google docs before pinning
    validation_alias=AliasChoices("PRIMARY_LLM_MODEL", "MODEL_NAME"),
)
```
Also make unknown/ignored env keys **warn** at startup in development (compare `.env` keys to `Settings.model_fields` aliases) so this class of bug can't hide again.
- `ModelProvider` has both `GOOGLE` and `GEMINI`. Collapse to one canonical value, accept the other as alias.
- **Embedding mismatch:** user config has `EMBEDDING_PROVIDER=openai` but a Gemini embedding model name and an empty `OPENAI_API_KEY`; `EMBEDDING_DIMENSIONS=1536` is hardcoded in `DocumentChunk.embedding = Vector(1536)`. Add a startup validator: provider/model consistent, API key present for the chosen provider, and `settings.embedding_dimensions == DB vector dimension` (query `pg_attribute`/`atttypmod` or a model constant). Refuse to start on mismatch. For Gemini embeddings with reduced dimensions, request the output dimensionality explicitly and L2-normalize when not using the model's native size. Record `embedding_model` + `embedding_version` per chunk (columns exist; make sure they are populated).
- **Production validator is too weak.** Extend `validate_production_settings` (also for `staging`): reject default `aura_internal_api_key`, default/short `postgres_password`, empty `redis_password`, `aura_debug`, wildcard or `http://localhost` CORS origins, `aura_log_format != json`, missing key for the selected primary provider (and fallback provider), and `aura_api_base_url` not https.
- Add settings (with env names in `.env.example`): `AURA_RUN_MIGRATIONS_ON_STARTUP` (default true in dev, **false** elsewhere), `MCP_SERVER_URL`, `MCP_ENABLED`, `AURA_RLS_ENABLED`, `AURA_DB_APP_USER/PASSWORD` (non-owner runtime role), `AURA_OTEL_*`, `AURA_SENTRY_DSN`, `AURA_DAILY_ORG_BUDGET_USD`, `AURA_MAX_REQUEST_BYTES`, `AURA_TRUSTED_HOSTS`, JWT `iss`/`aud`, `AURA_DEMO_PASSWORD` (dev only), `AURA_AGENT_RUN_HEARTBEAT_SECONDS`.
- `aura_secret_key` and `aura_internal_api_key` must be different values; validate.
- Version is hardcoded `"0.1.0"` in two places: read from package metadata / `settings.app_version`.

### 1.2 `alembic/env.py`
- `config.set_main_option("sqlalchemy.url", settings.database_url)` breaks if the password contains `%` (ConfigParser interpolation). Use `settings.database_url.replace("%", "%%")`.
- `include_schemas=True` without a filter pulls in extension schemas; add `include_name`/`include_object` to restrict to `public` and ignore pgvector-created objects.
- Add `lock_timeout`/`statement_timeout` for migrations, `transaction_per_migration=True` where appropriate, and a `version_table` explicit name.
- Migrations must run as the **owner** role, the app as a **non-owner** role (see Phase 2 RLS). Provide `database_url_migrations` vs `database_url`.
- Add a CI check `alembic check` (model drift) and an up→down→up roundtrip on an empty DB. Fix the model/migration mismatch described in Phase 3 (models use generic `sa.JSON`; migrations use JSONB).
- Verify the single Alembic head; the earlier `fix_migration.py` hardcoded `down_revision='002_add_rag_tables'` and derived the revision from the filename. Confirm the chain is linear and correct.

### 1.3 `main.py` lifespan — production risks
Current behavior: every process runs `alembic upgrade head` at startup, then marks **all** `PENDING/RUNNING` agent runs `FAILED`.
- With the production `--workers 4`, four processes race to migrate; and a **restarting worker kills runs that other healthy workers are executing**. Fix:
  1. Migrations run in a dedicated one-shot `migrate` container/job (Compose service, K8s Job). Startup migration only when `AURA_RUN_MIGRATIONS_ON_STARTUP=true` (dev), guarded by a Postgres advisory lock:
  ```python
  def upgrade_with_lock(cfg: alembic.config.Config) -> None:
      eng = sa.create_engine(settings.database_url_sync)
      with eng.connect() as c:
          c.execute(sa.text("SELECT pg_advisory_lock(727274)"))
          try:
              alembic.command.upgrade(cfg, "head")
          finally:
              c.execute(sa.text("SELECT pg_advisory_unlock(727274)"))
  ```
  2. Resolve `alembic.ini` path from `Path(__file__)`, not CWD.
  3. Stuck-run recovery uses **leases**: add `worker_id` + `heartbeat_at` to `agent_runs`; workers heartbeat every N seconds; recovery marks a run failed only if `heartbeat_at < now() - 3*N`. Never touch runs in `WAITING_APPROVAL` (check the real enum value names).
- Move imports out of the lifespan body; store clients on `app.state` (redis, mcp manager, llm router, tool registry, cost manager). Redis check with retry/backoff before failing.
- Add `/ready` (DB `SELECT 1`, Redis ping, alembic at head, MCP optional) separate from `/health` (liveness, no dependencies).
- Graceful shutdown: stop accepting runs, wait up to `AURA_SHUTDOWN_GRACE_SECONDS` for in-flight runs, then persist state and close MCP, Redis, DB (await any cancelled tasks).
- Middleware: current CORS comment contradicts ordering. Add, in order: `TrustedHostMiddleware`, request-size limit, security headers (HSTS, `X-Content-Type-Options`, `X-Frame-Options`/frame-ancestors, `Referrer-Policy`, CSP for API docs), `RequestIDMiddleware`, **rate limiting** (settings `aura_rate_limit_*` exist but I saw no limiter), CORS with explicit methods/headers in production (not `*` with credentials). Docs/OpenAPI disabled in staging too.
- **MCP mount:** `main.py` does `app.mount("/api/v1/mcp", asgi_sse)`. Confirm it is **authenticated** (internal API key and/or mTLS, tenant context required) and not reachable from the public internet through the gateway. Decide ONE topology: in-process mount (current) or separate `mcp-server` container. The old `update_docker.py`/`update_main.py` tried both at once. Document the decision in `docs/adr/0001-mcp-topology.md`.

### 1.4 Dockerfile (rewrite; current problems)
- Builder installs `".[dev]"` and the production stage copies it: **dev tooling ships to prod** while a comment claims "production deps only".
- `COPY pyproject.toml .` then `uv pip install ".[dev]"` without source: fragile; no lockfile (`uv.lock`), so builds aren't reproducible.
- Runtime installs `libpq-dev` (needs only `libpq5`); `curl` just for healthcheck; `COPY . .` can include `.env`/tests; `uv==0.4.18` is old; no `PYTHONUNBUFFERED`; base image not pinned by digest.
Target structure:
```dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:<PINNED> /uv /usr/local/bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
FROM base AS development
# + dev deps, source bind-mounted, uvicorn --reload
FROM base AS production
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/* \
 && groupadd -g 1001 aura && useradd -u 1001 -g aura -m aura
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" WEB_CONCURRENCY=4
WORKDIR /app
COPY --chown=aura:aura app ./app
COPY --chown=aura:aura alembic.ini migrations ./
USER aura
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers","--no-server-header"]
```
Generate and commit `uv.lock`. Add Trivy scan target and `--read-only` + tmpfs friendliness.

### 1.5 Docker Compose
Provide `docker-compose.yml` (base), `docker-compose.dev.yml` (bind mounts, reload, exposed ports) and `docker-compose.prod.yml`. (`docker-compose.override.yml` is in `.gitignore`, so don't rely on it for shared dev config.) Services: `postgres` (image `pgvector/pgvector:pg16`, healthcheck, volume), `redis` (password, AOF, **no host port in prod**), `migrate` (one-shot, owner role, `depends_on: postgres healthy`, `restart: "no"`), `api` (depends on `migrate: service_completed_successfully`), `worker` (Phase 4), `mcp-server` only if ADR chooses it, `frontend`, optional `otel-collector`/`prometheus`/`grafana` profile. Use `docker compose` (v2) everywhere. Python-based healthchecks (no curl dependency). Resource limits, `restart: unless-stopped`, named networks, no secrets in compose (use `env_file`/Docker secrets).

### 1.6 Scripts
- `setup.sh`: Python check is wrong (awk decimal compare passes 3.9 as ≥3.12). Use `python3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,12) else 1)'`. Switch `docker-compose` → `docker compose`. Load `.env` before reading `POSTGRES_USER`/`POSTGRES_DB`. Add a `setup.ps1` for Windows (or document WSL2). Add a `Makefile`/`justfile` (`make up|down|migrate|test|lint|seed|smoke`).
- `smoke_test.py`/`qa_smoke_test.py`/`verify_demo.py`: merge into one `scripts/smoke.py` (see Phase 10). `ping_health_endpoint` is defined but never called; endpoints disagree (`/health` vs `/api/v1/health`).

**Acceptance:** `docker compose up` from a clean clone works; `migrate` runs once; `/health` and `/ready` behave; image has no dev deps, no `.env`, runs non-root; settings refuse to boot in `production` with weak config (unit tests for each rule).

---

# PHASE 2 — Authentication, authorization, tenant isolation (highest priority)

### 2.1 Tenant identity comes from the token, never the request
Today the eval endpoints compare `current_user.organization_id` to `req.organization_id` taken from the **client body**, and several endpoints (`/benchmarks`, `/datasets`, `/datasets/evaluate`) check auth but not tenant scope. Replace with:
```python
@router.post("/safety")
async def evaluate_safety(req: EvaluateSafetyRequest, ctx: TenantCtx = Depends(tenant_ctx)) -> SafetyScore:
    org_id = ctx.organization_id   # from JWT only
```
Remove `organization_id` from request schemas (or ignore and log a warning if supplied). Apply a **router-level** `dependencies=[Depends(get_current_user)]` to every router (agent, eval, conversations, knowledge-bases, approvals, mcp, admin) so a new endpoint can't accidentally ship unauthenticated. For resources owned by another tenant return **404**, not 403, to prevent ID enumeration. Add a pytest that enumerates `app.routes` and fails if any route lacks an auth dependency unless it is in an explicit allowlist (`/health`, `/ready`, `/docs` in dev, `/auth/token`, `/auth/refresh`).

### 2.2 Postgres Row-Level Security (defense in depth — your diagram promises tenant isolation, today it's only app code)
- Two roles: `aura_owner` (migrations, owns tables) and `aura_app` (`NOSUPERUSER NOBYPASSRLS`, runtime). Create them idempotently in a **migration** (not only `init-db.sql`, which runs once on first volume creation).
- For every tenant table (including those lacking `organization_id` today: `tool_calls`, `eval_examples`, `eval_results` — add a denormalized `organization_id`):
```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <t>
  USING (organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid)
  WITH CHECK (organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid);
```
Unset setting ⇒ NULL ⇒ no rows (fail closed).
- Set the tenant per transaction (use `set_config`, because `SET LOCAL` can't take bind params):
```python
@event.listens_for(Session, "after_begin")
def _bind_tenant(session, transaction, connection):
    org = session.info.get("org_id")
    if org is not None:
        connection.execute(sa.text("SELECT set_config('app.current_org', :o, true)"), {"o": str(org)})
```
and set `session.info["org_id"]` in the `get_db` dependency from the verified JWT. Background workers must set it explicitly from the run's `organization_id`. Platform-admin/cross-tenant jobs use a separate, audited role.
- Tests with **two orgs** proving isolation at the DB layer (query without WHERE returns only own rows) and at the API layer for **every endpoint** (generated from the AUDIT.md table).
- `audit_events` and `tool_execution_audits`: append-only. `REVOKE UPDATE, DELETE` from `aura_app` and/or a trigger raising on UPDATE/DELETE; add `prev_hash`/`row_hash` (hash chain) for tamper evidence. Change their `ondelete="CASCADE"` from `organizations` to `RESTRICT` (deleting a tenant must not silently erase the audit trail; use soft-delete + retention jobs).

### 2.3 Authentication
- Password hashing: **argon2id** (`argon2-cffi`) with rehash-on-login; keep bcrypt verify for legacy. `User.hashed_password String(128)` fits argon2.
- JWT: separate `access` (short, 10-15 min) and `refresh` tokens; claims `sub, org, role, jti, iat, nbf, exp, iss, aud, typ`; validate all. **Refresh-token rotation with reuse detection** stored in DB/Redis (`refresh_tokens`: jti, user_id, family_id, revoked_at, expires_at); logout and "revoke all sessions" endpoints; token blocklist on password change/user deactivation. Consider RS256/EdDSA with key rotation (`kid`) instead of HS256 shared secret.
- Login protection: per-IP and per-account rate limits + progressive lockout in Redis; constant-time responses (no user enumeration); audit every login success/failure with IP and user agent.
- **RBAC:** today only `is_superuser` exists (and `role` lives in free-form `metadata_`). Add `role` enum on user-in-org (`owner|admin|manager|member|viewer`), a permission matrix in code (`app/core/permissions.py`), and `require_role(...)`/`require_permission("approval:decide")` dependencies. Enforce server-side on approvals, KB management, eval, user admin, tool-risk overrides. Frontend hiding is cosmetic only.
- API keys for service-to-service/programmatic use: hashed at rest, prefix-identifiable, scoped to org and permissions, revocable, last-used tracked.
- SSO (OIDC) design stub and MFA (TOTP) as a documented extension point; implement if time allows.
- Prompt-injection and abuse inputs: max lengths, content-type checks, Pydantic `extra="forbid"` on request models.

### 2.4 Rate limiting and abuse
Implement a Redis sliding-window/token-bucket limiter (atomic Lua) keyed by `org:user:route-class`, with stricter limits on `/auth/*`, agent runs and file uploads; return `429` with `Retry-After`. Per-tenant concurrent-run cap.

**Acceptance:** route-enumeration test passes; two-tenant matrix passes at API and DB layers; RLS verified with a non-owner connection; refresh rotation + reuse detection tested; no endpoint accepts `organization_id` from the client.

---

# PHASE 3 — Data model hardening (`models.py`, new migration)

Findings from review (fix each with a migration, data-preserving):

1. **Tenant-unsafe primary keys:** `Customer`, `Product`, `Quotation` use `id: String(50)` as a **global** PK. Two tenants can't both have `CUST-001`; inserting collides or leaks existence. Change to UUID PK + `code`/`sku` string with `UniqueConstraint("organization_id", "code")`; `Quotation.customer_id` → UUID FK. Migrate existing rows.
2. **Money as `Float`/`String`:** `Product.base_price` is `Float`, `Quotation.total` is `String(50)`. Use `Numeric(14,2)` + `currency` (ISO-4217 `String(3)`), compute with `Decimal`. Add `Quotation` line-items table (`quotation_items`: product_id, qty, unit_price, discount, tax) instead of a JSON blob, `valid_until`, `created_by`, `approved_by`, `approval_id`, `status` as enum, `version`.
3. **Idempotency not enforced:** `Quotation.idempotency_key` is nullable and non-unique. Add partial unique index `(organization_id, idempotency_key) WHERE idempotency_key IS NOT NULL`. Same for `tool_execution_audits` where it is meaningful.
4. **Naive vs aware datetimes:** `User.last_login_at`, `ApprovalRequest.actioned_at/expires_at` are `Mapped[datetime]` without timezone ⇒ naive columns mixed with tz-aware ones. Make **all** timestamps `DateTime(timezone=True)`. Add a `TimestampMixin` (`created_at`, `updated_at` server-side) and apply to every table (`customers`, `products`, `quotations`, `tool_execution_audits`, `agent_trace_events` lack them).
5. **JSON vs JSONB:** models use generic `sa.JSON`; migrations use JSONB. Use `sa.JSON().with_variant(JSONB(), "postgresql")` and add GIN indexes where queried. Since you need pgvector, RLS and JSONB, stop testing against SQLite (see Phase 9) and use Postgres.
6. **Missing indexes:** several `__table_args__ = ()` are empty (ToolCall, ApprovalRequest, AuditEvent). Add composites for real query patterns: `(organization_id, created_at DESC)` on runs/conversations/audits, `(organization_id, status)` on approvals (+ partial index for `PENDING`), `(agent_run_id, started_at)`, `(organization_id, started_at)` on `tool_execution_audits`, `(run_id, sequence)` unique on `agent_trace_events`.
7. **`EvalRun.completed_at` bug:** `server_default=now()` stamps completion at creation. Make nullable, add `started_at`, set on completion.
8. **Approval integrity:** add `args_hash` (sha256 of canonical tool args), `requested_by_id`, `tool_call_id`, and enforce `expires_at NOT NULL`. See Phase 4.
9. **Vector:** `Vector(1536)` hardcoded. Source dimension from one constant shared with settings (and the Phase 1 validator). Add **HNSW** index: `Index("ix_chunks_emb_hnsw","embedding",postgresql_using="hnsw",postgresql_with={"m":16,"ef_construction":64},postgresql_ops={"embedding":"vector_cosine_ops"})`. Add stored `tsvector` generated column + GIN for lexical search. NOTE: Postgres FTS `ts_rank` is **not** BM25; DEMO.md claims "BM25 + pgvector". Either integrate true BM25 (ParadeDB `pg_search`) or rename to "hybrid FTS + vector with Reciprocal Rank Fusion" and implement RRF.
10. **Document ACL:** add `visibility`/`allowed_roles`/`allowed_user_ids` on `documents` (or KB) and unique `(knowledge_base_id, checksum, version)`.
11. `ToolCall` (agent tool calls) and `ToolExecutionAudit` overlap. Define the relationship (audit = immutable security record; tool_call = operational record), link them with FK, avoid double-writing divergent data.
12. `ToolExecutionAudit`: make `status`, `risk_level`, `source` enums (check constraints), add `request_id`, `approval_id`, `created_at`, `args_hash` (rename `input_hash`, length 64).
13. Add `llm_usage` table (org, run, provider, model, prompt_tokens, completion_tokens, cost_usd, latency_ms, created_at) for CostManager truth and billing; add `refresh_tokens`, `api_keys`, `outbox_events` (Phase 4).
14. Enforce enum values with DB check constraints (SAEnum uses `native_enum=False`; ensure `create_constraint=True` or add explicit checks).

**Acceptance:** `alembic upgrade head` on empty DB and on a copy of current data succeeds; `alembic check` shows no drift; downgrade works; all model tests green on Postgres.

---

# PHASE 4 — Agent execution reliability and safety

Read `agents/core/builtin_nodes.py`, `agents/services/agent_service.py`, `tools/executor.py`, `tools/registry.py`, the PolicyEngine and planner first.

### 4.1 `ExecutionNode` (from `fix_exec.py`) — issues
- `idempotency_key` is read from `action.arguments["_idempotency_key"]` → **LLM-controlled**. Generate it server-side and strip underscore-prefixed args before they reach tools:
```python
args = {k: v for k, v in action.arguments.items() if not k.startswith("_")}
canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
args_hash = hashlib.sha256(canonical.encode()).hexdigest()
idem_key = hashlib.sha256(f"{state.organization_id}:{state.run_id}:{state.step_id}:{action.action_type}:{args_hash}".encode()).hexdigest()
```
- **Audit-after-effect hazard:** `persist_tool_audit` runs after the tool; if it throws, the node fails although a side effect already happened. For WRITE/EXTERNAL tools: write a `started` audit row **before** executing (fail closed if this write fails), then update to `succeeded|failed` after (log, don't crash, if the final update fails; reconcile later). For READ tools, audit failure must not crash the run.
- `registry.get()` then `registry.execute()` double lookup; unknown-tool handling duplicated. One path.
- `dry_run=False` hardcoded → plumb from request/run config. Audit skipped when `db` kwarg missing → make `db` a required dependency, not optional kwargs.
- Add per-tool **timeout** (`asyncio.timeout`), bounded **retries with exponential backoff + jitter** only for idempotent/READ or idempotency-keyed tools, **circuit breaker** per tool/MCP server, and a result-size cap.
- Replace the `from datetime import datetime, UTC` → `timezone.utc` hack. The project is Python 3.12; use `datetime.UTC` consistently (verify why the environment needed the hack: wrong interpreter?).

### 4.2 PolicyEngine = single choke point
Enforce policy **inside the executor**, not in the planner or LLM-facing code, so no path bypasses it. Decision inputs: tool risk class (READ / WRITE / EXTERNAL / HIGH), org policy, user role, amount/threshold, environment, dry-run, per-run `max_tool_calls`. Outputs: `ALLOW | REQUIRE_APPROVAL | DENY`, with reason, written to audit.
- **Approval binding:** the approval row stores `args_hash`; on resume the executor recomputes the hash and refuses to run if it differs (prevents "approve A, execute B"). Check: not expired, status APPROVED, same org, approver has permission, approver ≠ requester for HIGH risk (four-eyes configurable), single-use (consumed atomically with `UPDATE … WHERE status='APPROVED' RETURNING`).
- Tool allowlist per org/role; unknown tools denied. **MCP-discovered tools are untrusted:** default `risk=HIGH`, require explicit admin enablement, schema-validate arguments and outputs, strip/rename to avoid shadowing built-ins, pass tenant context, size-limit outputs.

### 4.3 Prompt-injection defense (indirect)
- Treat RAG chunks, tool outputs, emails and web content as **untrusted data**: wrap in clearly delimited blocks with provenance tags, instruct the model that they are data not instructions.
- A WRITE/EXTERNAL tool call whose arguments originate from untrusted content requires approval or a deterministic validator (e.g., email recipient must exist in CRM).
- Output filter: PII/secret redaction (keys, tokens, card numbers), no raw system prompt or tool schema leakage, URL/markdown-image exfiltration blocking in rendered responses.
- Maintain an attack corpus (`EvalExample.is_attack`) and gate CI on it (Phase 9).

### 4.4 Durable execution and workers
The API process currently builds `AgentWorkflowService` per request, and `initialize()` (MCP connect + discover) ran per request in the patch scripts. Restructure:
- Agent runs execute in a **worker** (ARQ on your existing Redis is the lowest-friction choice; Temporal if you need heavy workflows). API enqueues and returns `run_id`; clients follow via SSE/WebSocket (`Last-Event-ID` resume) or polling.
- **Checkpoint** `AgentState` to Postgres after every node. A `WAITING_APPROVAL` run holds no worker; approval enqueues a resume job. Server restart must not lose or fail waiting runs.
- Heartbeat/lease (Phase 1.3), per-run overall timeout (`aura_agent_timeout_seconds`), cancellation endpoint, per-tenant concurrency cap, dead-letter queue and retries for infrastructure failures.
- Transactional outbox for side effects (`outbox_events`) so DB state and external effects can't diverge.
- Shared singletons created in lifespan: tool registry, MCP manager, LLM router.

### 4.5 Tool-specific correctness
- `customer.search`/`product.search`: enforce tenant filter, parameterized queries only, escape LIKE wildcards, `pg_trgm` index for fuzzy search (extension already enabled), confidence scoring, cap results; ambiguity → ask user to choose (as in your diagram).
- `pricing.calculate`/`quotation.create_draft`: `Decimal` math, currency, discount policy rules, validity date, idempotent create, never trust LLM-supplied prices (recompute server-side).
- `communication.create_email_draft`: draft only; sending is a separate EXTERNAL tool requiring approval; sanitize recipients/headers.
- Merge the duplicate naming: diagram uses `customer.search`, DEMO.md uses `retrieve_customer`/`create_quotation`. Pick dot-notation (`domain.action`) everywhere (code, DB `tool_name`, docs, evals).
- Fix SIM102 nesting in `tools/builtin/customers.py`, `products.py`, `registry.py` while here.

**Acceptance:** tests for: idempotent double-execute creates one quotation; approval for args A cannot execute args B; expired/consumed approval rejected; audit row exists even when tool crashes; restart during `WAITING_APPROVAL` resumes after approval; timeout/retry/circuit-breaker behavior; injection corpus passes.

---

# PHASE 5 — LLM layer, routing, cost control

- Review `ai/providers/google.py` (Gemini): native function-calling/structured output with schema validation + repair-retry; streaming; safety-settings handling; usage/token extraction; map provider errors to a typed hierarchy (`RateLimited`, `Timeout`, `ContentBlocked`, `AuthError`, `Transient`); `raise ... from err`.
- `LLMRouter`: retries (exponential + jitter, honor `Retry-After`), per-provider **circuit breaker**, ordered fallback chain from `fallback_llm_provider/model` and `max_model_fallbacks`, per-call timeout, request/response redaction in logs. `ModelRouter` tiers (`fast_model`, `reasoning_model`, `long_context_model`) must have **Gemini-valid defaults** (current defaults are OpenAI models); validate configured model ids at startup (cheap listing call, optional).
- **CostManager:** atomic per-org daily and monthly budgets in Redis (Lua `INCRBYFLOAT` with expiry) + durable `llm_usage` rows; pricing table in config (versioned, per model, input/output per 1M tokens); hard stop and soft-warning thresholds; per-run token cap; budget exceeded → clean user-facing message + audit event + alert. The `$0.005` figure in DEMO.md should come from real usage.
- Caching: semantic/response cache for deterministic READ prompts (keyed by org + normalized prompt + KB version), invalidated on KB change. Optional.
- Deterministic mode for evals (`temperature=0`, seed where supported).

**Acceptance:** provider failure triggers fallback in tests (fake provider); budget exhaustion blocks calls and is audited; usage rows match provider-reported tokens.

---

# PHASE 6 — RAG hardening

- **Tenant + ACL filter in SQL**, before ranking: `WHERE organization_id = :org AND knowledge_base_id = ANY(:permitted_kbs) AND document.is_latest`. Never filter after retrieval.
- Hybrid retrieval: vector (HNSW, `ef_search` tuned) + lexical (FTS/BM25) fused with **RRF**, optional cross-encoder/LLM reranker, MMR for diversity, similarity threshold from settings, `top_k` caps.
- Ingestion pipeline as a worker job: type/size/magic-byte validation, optional AV-scan hook, text extraction with fallbacks (PDF/DOCX/XLSX/HTML/MD), structure-aware chunking (headings, tables), dedupe by checksum, versioning (`is_latest`), batch embeddings with retry/backoff and rate-limit awareness, partial-failure handling (`DocumentStatus.FAILED` with reason), idempotent re-ingest, re-embedding migration path when the embedding model changes.
- Citations: every answer carries `chunk_id`, document, page/section; VerificationNode computes `citation_correctness` against real chunks; "no answer found" path instead of guessing; groundedness check before returning.
- Evaluate with retrieval metrics (recall@k, MRR, nDCG) on a golden set in CI.

---

# PHASE 7 — MCP lifecycle and security

- Check the installed `mcp` SDK version; the **SSE transport is legacy** in the MCP spec in favor of **Streamable HTTP**. Migrate server and client if supported (keep SSE for compatibility only if needed).
- Single long-lived `MCPClientManager` created in lifespan (not per request), with reconnect/backoff, health status exposed in `/ready` (non-fatal), tool discovery refresh on interval + manual admin refresh, per-server timeouts.
- Server side: authenticate every call (internal key/mTLS/OAuth), enforce tenant context (tenant id comes from the authenticated principal, not from tool arguments), apply the same PolicyEngine and audit writes as in-process tools, rate limit, expose only allowlisted tools.
- Client side: treat remote tool names/descriptions/schemas as **untrusted prompt input** (tool-poisoning risk): sanitize descriptions, cap length, pin schemas by hash, require admin approval for newly appearing or changed tools.
- Remove the `httpx2` import (Phase 0) and clean unused imports in `mcp/server.py` and `mcp/routes.py`.

---

# PHASE 8 — Observability, operations, resilience

- **Tracing:** OpenTelemetry for FastAPI, SQLAlchemy, httpx, Redis; propagate W3C `traceparent`; one trace per agent run with spans per node/tool/LLM call (`AgentTraceEvent` stays as the durable business trace). Put `request_id`/`trace_id`/`organization_id`/`run_id` in every log line via contextvars; store `request_id` on audit rows.
- **Metrics (`/metrics`, internal only):** request latency/error rate, agent run duration/outcome, tool latency/error by tool, LLM latency/tokens/cost by model, approval wait time, queue depth, DB pool saturation, RAG retrieval latency, rate-limit hits, budget usage by org. Ship Grafana dashboards + alert rules (error budget, p95 latency, queue lag, budget exhaustion, auth-failure spikes, audit-write failures).
- LLM observability (Langfuse or OTel GenAI semantic conventions), Sentry for exceptions (scrub PII).
- Log hygiene: redact secrets/PII/tokens (processor in structlog), never log full prompts/tool args in production by default, sampling for debug.
- DB: pool settings per worker count (`pool_size × workers × replicas` must stay under `max_connections`; consider PgBouncer), `statement_timeout`, `idle_in_transaction_session_timeout`, slow-query logging, backups (pg_dump/WAL-G + restore drill documented in `docs/RUNBOOK.md`), retention jobs for traces/audit with legal-hold flag.
- Resilience: graceful degradation when MCP/LLM/Redis is down (clear error to user, no crash), idempotent endpoints, request timeouts, bulkheads (separate pools/semaphores for LLM calls vs DB).

---

# PHASE 9 — Tests, evaluation gates, CI/CD

Correction to my earlier note: you **do** have a pytest suite under `backend/tests`. Keep and extend it.

- **Switch the DB layer of tests to real Postgres** (`pgvector/pgvector:pg16` via testcontainers or a CI service). SQLite cannot test RLS, pgvector, JSONB, partial indexes or advisory locks, and `models.py` currently contorts itself for SQLite.
- Must-have tests: tenant isolation matrix (API + DB/RLS), route-auth enumeration, JWT/refresh rotation/reuse, RBAC matrix, rate limiting, idempotency, approval binding/expiry, audit immutability (UPDATE/DELETE denied), policy decisions table-driven, execution timeout/retry/circuit-breaker, crash/resume of waiting runs, settings production validators, migration up/down/check, RAG ACL filtering and citation correctness, MCP auth + tool-poisoning rejection, LLM fallback and budget enforcement (fake provider), prompt-injection corpus.
- Property/fuzz: Hypothesis on pricing math and argument canonicalization; Schemathesis against the OpenAPI schema.
- Frontend: Playwright e2e for login → ask → approval → result, plus a11y checks; component tests for the approval diff view.
- Coverage gate (≥80% on `app/agents`, `app/tools`, `app/api`, `app/security`); mypy strict on new code, gradually tightened.
- **Eval gate:** golden-dataset + attack-set evaluation (`EvalDataset/EvalRun`) executes in CI against the Mock/Heuristic provider deterministically; a scheduled nightly run against real Gemini with thresholds (success rate, safety, citation correctness, cost per task). Regressions fail the build.
- **GitHub Actions:** `ci.yml` (ruff, ruff format, mypy, pytest with Postgres+Redis services, alembic upgrade/check/downgrade, frontend lint/typecheck/build/Playwright), `security.yml` (pip-audit, bandit, gitleaks, Trivy image+fs, CodeQL, `npm audit`), `release.yml` (build/push images with SBOM + provenance, tag by git SHA). Dependabot/Renovate. `pre-commit` with ruff, gitleaks, end-of-file/line-ending hooks, conventional commits. Branch protection documented.

---

# PHASE 10 — Seed/demo consistency, frontend, documentation

### 10.1 Seed and verification mismatch
`seed_data.py` creates `admin@acme.example.com` with **no password**, 2 conversations and no runs/approvals/KBs; `verify_demo.py` logs in as `demo@aura-sre.com / demo1234` and expects ≥15 runs, ≥3 approvals, ≥15 conversations, ≥6 knowledge bases. They cannot pass together. Rewrite as one idempotent (upsert) seeder `scripts/seed_data.py` that:
- **Refuses to run when `AURA_ENV != development`.**
- Creates org(s), users per role (owner/admin/manager/member/viewer) with argon2 hashes from `AURA_DEMO_PASSWORD` (never a hardcoded password in the repo), a **second tenant** (for isolation demos), customers/products/pricing, ≥6 KBs with real documents + embeddings (or mock embeddings flagged as such), ≥15 conversations, ≥15 agent runs across statuses, ≥3 pending approvals, audit and trace events, eval datasets with attack cases.
- Uses the model-layer APIs consistent with Phase 3 (UUID PKs, tz-aware timestamps).
- Replace `verify_demo.py`, `smoke_test.py`, `qa_smoke_test.py` with one `scripts/smoke.py`: timeouts on every request, status-code checks **before** `.json()`, retries while the stack warms, exit codes, `--env` flag, endpoints `/health`, `/ready`, login, a tenant-isolation probe (user A cannot read org B), one full agent run with approval. Never require host ports 5432/6379 (they should not be exposed in prod).

### 10.2 Frontend (not reviewed — audit first)
Verify and fix: access token storage (prefer httpOnly + SameSite cookies with CSRF protection over `localStorage`), silent refresh handling, 401/403/429 UX, strict CSP and security headers in `next.config`, no secrets in `NEXT_PUBLIC_*`, typed API client generated from the backend OpenAPI (`openapi-typescript`), TypeScript `strict`, error boundaries, loading/streaming states for agent progress, **approval screen shows the exact tool and arguments (diff) that will execute and binds to the approval's `args_hash`**, role-aware UI (server still enforces), accessibility (WCAG AA), responsive layout, i18n readiness, Sentry.

### 10.3 Documentation
- Update the architecture diagram/source (Mermaid in repo): add **ModelRouter, PolicyEngine, Approval/HITL, CostManager, Evaluators, Worker queue, Redis, RLS, MCP topology**, which DEMO.md describes but the diagram omits. Align all tool names (Phase 4.5).
- `README.md` (quickstart for Windows/WSL + Linux/macOS), `ARCHITECTURE.md`, `SECURITY.md` (threat model: STRIDE + prompt-injection/"lethal trifecta" analysis, trust boundaries, data classification), `RUNBOOK.md` (deploy, rollback, backup/restore, incident response, key rotation), `CONTRIBUTING.md`, `docs/adr/*`, `CHANGELOG.md`, `.env.example` fully synced with `Settings` (every field, with comments, no real values), `LICENSE` (main.py says MIT; confirm).
- Fix `main.py` placeholder contact URL (`https://github.com/your-org/aura`).

---

## FINAL DEFINITION OF DONE (after Phase 10)

- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` from a clean clone → healthy, migrated once, non-root, no dev deps, no secrets in image
- [ ] Production boot refuses weak config; secrets only from env/secret manager
- [ ] Every route authenticated except an explicit allowlist (test-enforced); tenant derived from token; RLS on every tenant table and proven with a non-owner role
- [ ] Refresh rotation + reuse detection, argon2id, RBAC server-side, rate limits, lockout
- [ ] No tool executes without policy decision; approvals bound to args hash, single-use, expiring; audit written before effects for WRITE/EXTERNAL; audit is append-only
- [ ] Agent runs are durable (worker + checkpoints); restart-safe; leases not blanket recovery
- [ ] LLM fallback, circuit breakers, per-org budgets enforced and audited
- [ ] RAG filtered by tenant/ACL in SQL, hybrid search with citations verified
- [ ] MCP authenticated, tenant-aware, tools untrusted by default
- [ ] Traces, metrics, dashboards, alerts, backups + restore drill documented
- [ ] CI green: lint, types, tests (Postgres), migrations, security scans, evals, e2e
- [ ] One consistent seed + smoke script; docs and diagram match the code

## FIRST ACTION

Start **Phase 0** now. Do not begin Phase 1 until I reply `continue`. If any file referenced above does not exist at the stated path, search for it, state where it actually lives, and proceed.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-01T13:29:11+05:30.
</ADDITIONAL_METADATA>