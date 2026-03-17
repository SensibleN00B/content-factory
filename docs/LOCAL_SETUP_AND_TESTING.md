# Local Setup and Testing Guide

This runbook documents how to set up, run, and verify the project locally.

## 1. Prerequisites

- Windows PowerShell (`pwsh`)
- Git
- Docker Desktop (Compose v2)
- `uv` (Python package manager)
- Node.js + npm (required later for full frontend scaffold)

## 2. Project Bootstrap

From repository root:

```powershell
git pull
```

Copy environment template:

```powershell
Copy-Item .env.example .env
```

## 3. Backend Dependencies (uv)

Install backend dependencies:

```powershell
uv sync --project apps/api --group dev
```

## 4. Developer Checks

Install frontend dependencies:

```powershell
npm --prefix apps/web install
```

Run baseline checks from repository root:

```powershell
pwsh ./scripts/lint.ps1
pwsh ./scripts/format.ps1
pwsh ./scripts/test.ps1
```

Notes:
- Backend tests may show `Skipping...` if `apps/api/tests` does not exist yet.

## 5. Run with Docker Compose

Start stack (`api + db + web`):

```powershell
docker compose -f infra/docker-compose.yml up --build -d
```

Verify services:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:5173
```

Expected:
- API health returns `{\"status\":\"ok\"}`
- Web endpoint returns status `200`

Stop stack:

```powershell
docker compose -f infra/docker-compose.yml down
```

## 6. Progress Tracking and Resume

- Canonical backlog: `docs/plans/2026-03-13-trend-discovery-web-mvp-backlog.md`
- Date split: `docs/plans/2026-03-13-16-17-backlog-split.md`
- Current status: `docs/logs/CURRENT_STATUS.md`
- Session logs: `docs/logs/YYYY-MM-DD-session.md`

Resume workflow:
1. Open `docs/logs/CURRENT_STATUS.md`.
2. Check the latest session file for context.
3. Continue from the `Next Up` ticket.

## 7. Common Issues

1. `docker compose` fails to start:
- Ensure Docker Desktop is running.
- Check ports `5432`, `8000`, and `5173` are not occupied.

2. `uv` command not found:
- Install uv and re-open terminal.

3. `npm --prefix apps/web run lint` fails because `tsc` is missing:
- Run `npm --prefix apps/web install`.
