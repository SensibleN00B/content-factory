$ErrorActionPreference = "Stop"

Write-Host "==> Format: backend (Python via uv)"
if (Test-Path "apps/api/pyproject.toml") {
    uv run --project apps/api --group dev ruff format .
} else {
    Write-Host "Skipping backend format: apps/api/pyproject.toml not found."
}

Write-Host "==> Format: frontend (Node)"
if (Test-Path "apps/web/package.json") {
    npm --prefix apps/web run format --if-present
} else {
    Write-Host "Skipping frontend format: apps/web/package.json not found."
}

Write-Host "Format step finished."
