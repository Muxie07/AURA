# AURA Deployment

Two deployment shapes are documented here:

1. **Free-tier demo deployment** (below) — what this project actually uses for its live portfolio demo. $0/month, one disclosed tradeoff (no separate background worker — agent runs inline in the request handler; see `AURA_FORCE_INLINE_EXECUTION` in `app/config/settings.py`).
2. **Full container deployment** (bottom of this doc) — Docker Compose / Kubernetes, with a real ARQ worker, for anyone who wants to run this as designed rather than as a free demo.

---

## Free-tier demo deployment ($0/month)

| Component | Provider | Why |
| :--- | :--- | :--- |
| Frontend (Next.js) | [Vercel](https://vercel.com) Hobby | Free, built for Next.js, no card required |
| Postgres + pgvector | [Neon](https://neon.tech) Free | pgvector on every plan, auto-wakes on query (no manual "restore" like some competitors) |
| Redis | [Upstash](https://upstash.com) Free | 500K commands/month, covers rate limiting + would cover ARQ if a worker were added later |
| Backend API | [Render](https://render.com) Free Web Service | $0, cold-starts (~30-50s) after idle — acceptable for a demo link |
| Background worker | **None** | No platform offers a genuinely free always-on worker. `AURA_FORCE_INLINE_EXECUTION=true` runs the agent synchronously in the API process instead. Disclosed in the README's Known Limitations. |

### Step 1 — Neon (Postgres + pgvector)

1. Create a free project at neon.tech.
2. Open the SQL editor on your new database and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. From the connection string Neon gives you (`postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require`), pull out the pieces — you'll set these as separate env vars on Render, not as one `DATABASE_URL` (this backend builds its DSN from discrete fields):
   - `POSTGRES_HOST` = the host part
   - `POSTGRES_PORT` = `5432`
   - `POSTGRES_USER` = USER
   - `POSTGRES_PASSWORD` = PASSWORD
   - `POSTGRES_DB` = DBNAME
   - `POSTGRES_SSL_REQUIRE` = `true` (Neon requires TLS; this flag appends `?ssl=require` to the DSN)

### Step 2 — Upstash (Redis)

1. Create a free Redis database at upstash.com, same region as your Render service if possible (lower latency).
2. From the connection details, set:
   - `REDIS_HOST`
   - `REDIS_PORT`
   - `REDIS_PASSWORD`
   - `REDIS_SSL_REQUIRE` = `true` (Upstash requires TLS; switches the scheme to `rediss://`)

### Step 3 — Render (backend)

1. New Web Service → connect this GitHub repo → root/Dockerfile path `backend/Dockerfile`, target stage `production`.
2. Free instance type.
3. Environment variables (minimum set):
   ```
   AURA_ENV=production
   AURA_DEBUG=false
   AURA_SECRET_KEY=<openssl rand -hex 32>
   AURA_INTERNAL_API_KEY=<a different openssl rand -hex 32>
   AURA_FORCE_INLINE_EXECUTION=true
   POSTGRES_HOST=...          # from Step 1
   POSTGRES_PORT=5432
   POSTGRES_USER=...
   POSTGRES_PASSWORD=...
   POSTGRES_DB=...
   POSTGRES_SSL_REQUIRE=true
   REDIS_HOST=...             # from Step 2
   REDIS_PORT=...
   REDIS_PASSWORD=...
   REDIS_SSL_REQUIRE=true
   GEMINI_API_KEY=...         # or OPENAI_API_KEY / ANTHROPIC_API_KEY
   LLM_PROVIDER=google
   AURA_CORS_ORIGINS=["https://your-frontend.vercel.app"]
   AURA_FRONTEND_BASE_URL=https://your-frontend.vercel.app
   AURA_DEMO_PASSWORD=<pick something other than the default if you want>
   ```
   `AURA_SECRET_KEY` and `AURA_INTERNAL_API_KEY` must each be 32+ characters and different from each other — `settings.py` enforces this in production and will refuse to start otherwise.
4. Deploy. Watch the logs for the Alembic migration step (or run it manually once via Render's Shell tab: `alembic upgrade head`).
5. Seed the demo data **once**, via Render's Shell tab:
   ```bash
   AURA_ALLOW_SEED=true python scripts/seed_data.py
   ```
   This creates the two demo accounts (`demo@aura-sre.com`, `admin@aura-sre.com`) with the password from `AURA_DEMO_PASSWORD` (or `demo1234` if unset), five demo customers, and 15 sample agent runs. It's also what backs the pre-filled login form.

### Step 4 — Vercel (frontend)

1. Import the repo, set the project root to `frontend/`.
2. Environment variable: `NEXT_PUBLIC_API_URL=https://your-backend.onrender.com/api/v1`
3. Deploy. Once you have the real Vercel URL, go back to Render and update `AURA_CORS_ORIGINS` / `AURA_FRONTEND_BASE_URL` to match it exactly, then redeploy the backend.

### What to expect from this setup

- First request after idle on Render's free tier takes 30-50 seconds (cold start). Mention this if sharing the link cold; it feels broken for the first ~40s and then isn't.
- Agent runs execute inline in the request/response cycle, not through the ARQ queue — fine for demo traffic, not how the architecture is designed to run at real scale (see README → Known Limitations).
- Gmail/SMTP approval emails won't actually send unless you also configure `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` or SMTP app-password vars — the approval UI and flow still work end-to-end (approve/reject, audit trail), the email delivery step is just optional for a free deployment.

---

## Full container deployment (with a real worker)

AURA is container-native and designed to be deployed onto Kubernetes or a managed PaaS that supports a persistent worker process (Render paid Background Worker, Railway, a VM, etc.).

### Requirements
- PostgreSQL 15+ (with `pgvector` extension)
- Redis 7+
- Docker Engine

### Local execution
```bash
docker-compose up -d --build
```

### Environment configuration
Copy `.env.example` to `.env` and fill out your secrets. Key variables:
- `AURA_SECRET_KEY` — 32+ chars in production.
- `AURA_INTERNAL_API_KEY` — 32+ chars, different from `AURA_SECRET_KEY`, required in production.
- `AURA_ENV=production` — activates the strict validations above.
- `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` — there is no single `DATABASE_URL` env var; the DSN is assembled from these.
- `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — at least one LLM provider key.
- `AURA_FORCE_INLINE_EXECUTION` — leave unset/`false` for a real deployment; this should only be `true` on a demo with no worker.

### Migrations
Run automatically on backend container startup, or manually:
```bash
docker compose exec backend alembic upgrade head
```

### Background worker
```bash
docker compose up -d worker   # runs app/worker.py via arq
```
This is the piece the free-tier path above skips.

### Production notes
Use the `production` Dockerfile target. Don't expose MCP, Postgres, or Redis to the internet — only the frontend and backend API should sit behind a reverse proxy/load balancer.
