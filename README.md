# Content Factory

## Project Structure

- `apps/api` - FastAPI backend service (Python via `uv`)
- `apps/web` - React frontend application
- `packages/contracts` - Shared API contracts/types between frontend and backend
- `infra` - Local infrastructure assets (docker-compose, env templates, scripts)
- `docs/plans` - Planning and execution documents
- `docs/logs` - Current status and daily progress logs
- `project files` - Reference research materials and source files

## Package Management Policy

- Python package manager and runner: `uv` (required).
- JavaScript package manager: `npm` (for now, can switch later).
- Do not use `pip install` directly for project dependencies.

## Baseline Tooling Commands

- Install backend deps: `uv sync --project apps/api --group dev`
- Install frontend deps: `npm --prefix apps/web install`
- Lint: `pwsh ./scripts/lint.ps1`
- Format: `pwsh ./scripts/format.ps1`
- Test: `pwsh ./scripts/test.ps1`

## Docker Compose (OPS-001)

- Start stack: `docker compose -f infra/docker-compose.yml up --build -d`
- Stop stack: `docker compose -f infra/docker-compose.yml down`
- API health: `http://localhost:8000/health`
- Web endpoint: `http://localhost:5173`

## Environment Template

- Copy `.env.example` to `.env` and fill required keys as integrations are enabled.

## Progress Tracking

- Current state: `docs/logs/CURRENT_STATUS.md`
- Daily logs: `docs/logs/YYYY-MM-DD-session.md`

## Runbook

- Local setup and testing: docs/LOCAL_SETUP_AND_TESTING.md
- API and UI usage guide: docs/API_UI_USAGE_GUIDE.md

