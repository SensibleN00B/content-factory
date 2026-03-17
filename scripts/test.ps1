$ErrorActionPreference = "Stop"

Write-Host "==> Test: backend (Python via uv)"
if ((Test-Path "apps/api/pyproject.toml") -and (Test-Path "apps/api/tests")) {
    uv run --project apps/api --group dev pytest tests
} else {
    Write-Host "Skipping backend tests: apps/api/pyproject.toml or apps/api/tests not found."
}

Write-Host "==> Test: frontend (Node)"
if (Test-Path "apps/web/package.json") {
    npm --prefix apps/web run test --if-present
} else {
    Write-Host "Skipping frontend tests: apps/web/package.json not found."
}

Write-Host "Test step finished."
