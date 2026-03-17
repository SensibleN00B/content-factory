# API

Python backend managed with `uv`.

## Quick start

- Install deps: `uv sync --project apps/api --group dev`
- Lint: `uv run --project apps/api --group dev ruff check src tests`
- Format: `uv run --project apps/api --group dev ruff format src tests`
- Test: `uv run --project apps/api --group dev pytest tests`

## Database and Migrations

- Alembic config: `apps/api/alembic.ini`
- Show migration heads: `uv run --project apps/api alembic -c apps/api/alembic.ini heads`
- Show current revision: `uv run --project apps/api alembic -c apps/api/alembic.ini current`
- Create revision: `uv run --project apps/api alembic -c apps/api/alembic.ini revision -m "message"`
- Apply migrations: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
