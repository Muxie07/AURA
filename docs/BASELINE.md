# AURA — Phase 0 Baseline Report

## Testing (Pytest)
- **Status**: Passes (161 tests)
- **Notes**: Some warnings remain for Deprecations and asyncio scopes, but tests pass.

## Code Quality (Ruff)
- **Status**: 0 errors in application code and active tests.
- **Notes**: Legacy scripts ignored via `per-file-ignores` in `pyproject.toml` (will be removed/merged in Phase 10). `ruff format` applied cleanly.

## Type Checking (Mypy)
- **Status**: Baseline.

## Frontend
- **Status**: Lint and Build succeed locally.

## Git / Repository Hygiene
- Throwaway scripts deleted.
- `.gitignore` and `.dockerignore` updated.
- Line endings normalized (LF) and `.gitattributes` applied.
