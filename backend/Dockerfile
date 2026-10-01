# =============================================================================
# AURA Backend — Dockerfile
# Multi-stage build for development and production targets.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Python dependency builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# System dependencies required for psycopg2, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv==0.4.18

WORKDIR /build

# Copy dependency manifests first (layer caching)
COPY pyproject.toml .

# Install all dependencies (including dev extras for development stage)
RUN uv pip install --system --no-cache ".[dev]"

# -----------------------------------------------------------------------------
# Stage 2: Development image
# Hot-reload via uvicorn --reload, source mounted as volume
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# In development, source is mounted as a volume (see docker-compose.yml)
# This CMD is the fallback when running the container directly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# -----------------------------------------------------------------------------
# Stage 3: Production image
# Minimal attack surface, non-root user, no dev tools
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 aura \
    && useradd --uid 1001 --gid aura --shell /bin/bash --create-home aura

# Copy installed packages from builder (production deps only)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy application source
COPY --chown=aura:aura . .

# Switch to non-root user
USER aura

# Health check — mirrors docker-compose.yml
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
