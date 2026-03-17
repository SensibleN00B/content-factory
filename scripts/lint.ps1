$ErrorActionPreference = "Stop"

Write-Host "==> Lint: backend (Python via uv)"
if (Test-Path "apps/api/pyproject.toml") {
    uv run --project apps/api --group dev ruff check .
} else {
    Write-Host "Skipping backend lint: apps/api/pyproject.toml not found."
}

Write-Host "==> Lint: frontend (Node)"
if (Test-Path "apps/web/package.json") {
    npm --prefix apps/web run lint
} else {
    Write-Host "Skipping frontend lint: apps/web/package.json not found."
}

Write-Host "Lint step finished."
