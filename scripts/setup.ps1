Write-Host "[INFO] Starting AURA Setup..." -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required."
    exit 1
}

$pyCheck = python -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3.12+ is required."
    exit 1
}

if (-not (Test-Path .env)) {
    Write-Host "[INFO] Creating .env from .env.example..."
    Copy-Item .env.example .env
}

# Load .env variables
Get-Content .env | Where-Object { $_ -match '^[^#]+=' } | ForEach-Object {
    $name, $value = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($name, $value)
}

Write-Host "[INFO] Starting Docker services..."
docker compose up -d postgres redis

Write-Host "[INFO] Waiting for PostgreSQL..."
$timeout = 60
$postgresUser = [Environment]::GetEnvironmentVariable("POSTGRES_USER")
if (-not $postgresUser) { $postgresUser = "aura" }
$postgresDb = [Environment]::GetEnvironmentVariable("POSTGRES_DB")
if (-not $postgresDb) { $postgresDb = "aura" }

do {
    docker compose exec -T postgres pg_isready -U $postgresUser -d $postgresDb | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
    $timeout--
} while ($timeout -gt 0)

if ($timeout -eq 0) {
    Write-Error "Timed out waiting for PostgreSQL."
    exit 1
}

Write-Host "[SUCCESS] PostgreSQL is ready." -ForegroundColor Green

Write-Host "[INFO] Running database migrations..."
docker compose build db-migration
docker compose up db-migration
Write-Host "[SUCCESS] Migrations applied." -ForegroundColor Green

Write-Host "[SUCCESS] AURA is ready!" -ForegroundColor Green
