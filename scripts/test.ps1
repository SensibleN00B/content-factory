$ErrorActionPreference = "Stop"

Write-Host "==> Test: backend (Python via uv)"
if ((Test-Path "apps/api/pyproject.toml") -and (Test-Path "apps/api/tests")) {
    $env:PYTHONPATH = "apps/api/src"
    uv run --project apps/api --group dev pytest apps/api/tests
    $exitCode = $LASTEXITCODE
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    if ($exitCode -ne 0) { exit $exitCode }
} else {
    Write-Host "Skipping backend tests: apps/api/pyproject.toml or apps/api/tests not found."
}

Write-Host "==> Test: frontend (Node)"
if (Test-Path "apps/web/package.json") {
    npm --prefix apps/web run test --if-present
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Skipping frontend tests: apps/web/package.json not found."
}

Write-Host "Test step finished."
