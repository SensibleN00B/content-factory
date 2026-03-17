param(
    [switch]$SkipDockerChecks
)

$ErrorActionPreference = "Stop"

Write-Host "==> Smoke: lint"
pwsh ./scripts/lint.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Smoke: tests"
pwsh ./scripts/test.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDockerChecks) {
    Write-Host "==> Smoke: service health checks"

    $apiUrl = "http://localhost:8000/health"
    $webUrl = "http://localhost:5173"

    try {
        $apiResponse = Invoke-WebRequest -Uri $apiUrl -Method Get -TimeoutSec 10
        if ($apiResponse.StatusCode -ne 200) {
            throw "API health endpoint returned status $($apiResponse.StatusCode)"
        }
    } catch {
        Write-Error "API health check failed at $apiUrl. Ensure docker stack is running."
        exit 1
    }

    try {
        $webResponse = Invoke-WebRequest -Uri $webUrl -Method Get -TimeoutSec 10
        if ($webResponse.StatusCode -ne 200) {
            throw "Web endpoint returned status $($webResponse.StatusCode)"
        }
    } catch {
        Write-Error "Web check failed at $webUrl. Ensure web service is running."
        exit 1
    }
}

Write-Host "Smoke check passed."
