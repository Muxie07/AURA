#!/usr/bin/env bash
# =============================================================================
# AURA — Development Environment Setup Script
# =============================================================================
# Usage:
#   ./scripts/setup.sh
#
# What this does:
# 1. Validates system dependencies
# 2. Creates the .env file from .env.example (if not present)
# 3. Installs Python dependencies via uv
# 4. Starts Docker services (PostgreSQL, Redis)
# 5. Runs database migrations
# 6. Optionally seeds demo data
# =============================================================================

set -euo pipefail

# --- Colors ------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[AURA]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# 1. Dependency Checks
# =============================================================================
log "Checking system dependencies..."

command -v docker >/dev/null 2>&1 || error "Docker is required. Install from https://docker.com"
command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is required."
command -v python3 >/dev/null 2>&1 || error "Python 3.12+ is required."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$PYTHON_VERSION 3.12" | awk '{print ($1 >= $2)}') -ne 1 ]]; then
    error "Python 3.12+ is required. Found: $PYTHON_VERSION"
fi

success "Dependencies OK (Python $PYTHON_VERSION, Docker)"

# =============================================================================
# 2. Environment Configuration
# =============================================================================
if [[ ! -f "$ROOT_DIR/.env" ]]; then
    log "Creating .env from .env.example..."
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    warn "Please review and update $ROOT_DIR/.env with your settings."
    warn "Especially: POSTGRES_PASSWORD, AURA_SECRET_KEY, and API keys."
else
    success ".env already exists."
fi

# =============================================================================
# 3. Python Dependencies
# =============================================================================
log "Installing Python dependencies..."
cd "$ROOT_DIR/backend"

if command -v uv >/dev/null 2>&1; then
    uv pip install --system -e ".[dev]"
else
    warn "uv not found. Using pip (slower). Install uv: pip install uv"
    python3 -m pip install -e ".[dev]"
fi
success "Python dependencies installed."

# =============================================================================
# 4. Docker Services
# =============================================================================
log "Starting Docker services (PostgreSQL, Redis)..."
cd "$ROOT_DIR"
docker-compose up -d postgres redis

log "Waiting for PostgreSQL to be ready..."
timeout=60
until docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER:-aura}" -d "${POSTGRES_DB:-aura}" >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [[ $timeout -le 0 ]]; then
        error "Timed out waiting for PostgreSQL. Check: docker-compose logs postgres"
    fi
    sleep 1
done
success "PostgreSQL is ready."

# =============================================================================
# 5. Database Migrations
# =============================================================================
log "Running database migrations..."
cd "$ROOT_DIR/backend"
python3 -m alembic upgrade head
success "Migrations applied."

# =============================================================================
# 6. Seed Data
# =============================================================================
if [[ "${SEED:-true}" == "true" ]]; then
    log "Running seed data script..."
    python3 "$ROOT_DIR/scripts/seed_data.py" || warn "Seed data script failed (may be expected if already seeded)."
fi

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       AURA Setup Complete!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Start the backend:"
echo "    cd backend && uvicorn app.main:app --reload"
echo ""
echo "  Or with Docker:"
echo "    docker-compose up"
echo ""
echo "  API Docs: http://localhost:8000/docs"
echo "  Health:   http://localhost:8000/health"
echo ""
