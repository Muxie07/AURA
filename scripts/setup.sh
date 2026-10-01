#!/bin/bash
set -euo pipefail

log() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v docker >/dev/null 2>&1 || error "Docker is required."
if ! docker compose version >/dev/null 2>&1; then
    error "Docker Compose V2 is required (docker compose, not docker-compose)."
fi
command -v python3 >/dev/null 2>&1 || error "Python 3 is required."

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" || error "Python 3.12+ is required."

if [[ ! -f ".env" ]]; then
    log "Creating .env from .env.example..."
    cp .env.example .env
fi

# Load .env
export $(grep -v '^#' .env | xargs)

log "Starting Docker services..."
docker compose up -d postgres redis

log "Waiting for PostgreSQL..."
timeout=60
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-aura}" -d "${POSTGRES_DB:-aura}" >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [[ $timeout -le 0 ]]; then
        error "Timed out waiting for PostgreSQL."
    fi
    sleep 1
done
success "PostgreSQL is ready."

log "Running database migrations..."
docker compose build db-migration
docker compose up db-migration
success "Migrations applied."

success "AURA is ready!"
