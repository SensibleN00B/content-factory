# Content Factory

## Project Structure

- `apps/api` - FastAPI backend service (Python via `uv`)
- `apps/web` - React frontend application
- `packages/contracts` - Shared API contracts/types between frontend and backend
- `infra` - Local infrastructure assets (docker-compose, env templates, scripts)
- `docs/plans` - Planning and execution documents
- `project files` - Reference research materials and source files

## Package Management Policy

- Python package manager and runner: `uv` (required).
- JavaScript package manager: `npm` (for now, can switch later).
- Do not use `pip install` directly for project dependencies.

## Baseline Tooling Commands

- Install backend deps: `uv sync --project apps/api --group dev`
- Lint: `pwsh ./scripts/lint.ps1`
- Format: `pwsh ./scripts/format.ps1`
- Test: `pwsh ./scripts/test.ps1`

## Environment Template

- Copy `.env.example` to `.env` and fill required keys as integrations are enabled.

## Next Milestones

- `OPS-001`: Docker Compose for API, DB, and Web
- `DOC-001`: local setup and testing runbook
