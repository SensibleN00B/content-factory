# Current Status

## Project

- Name: Content Factory (Trend Discovery Web MVP)
- Canonical plan: `docs/plans/2026-03-13-trend-discovery-web-mvp-backlog.md`
- Date split: `docs/plans/2026-03-13-16-17-backlog-split.md`

## Last Updated

- Date: 2026-03-17
- Updated by: Codex

## Completed

- `ARCH-001`: monorepo skeleton created (`apps/api`, `apps/web`, `packages/contracts`, `infra`)
- `DEV-001`: baseline tooling and env templates
- `OPS-001`: Docker Compose stack for `api + db + web` implemented and smoke-tested
- `DOC-001`: local setup and testing runbook created
- `BE-001`: FastAPI layered app skeleton + health router + passing health test
- `BE-002`: SQLAlchemy session layer + Alembic wiring integrated and verified
- `BE-003`: core schema models + initial Alembic migration implemented and validated
- `BE-004`: profile API (`GET/PUT /api/profile`) with DB persistence + update-in-place behavior
- `BE-005`: run state machine with strict transition validation and terminal-state guards
- `BE-006`: run APIs implemented (`POST /api/runs`, `GET /api/runs/{id}`)
- `SRC-001`: source adapter contract (`SourceConnector`) + source registry
- `SRC-002`: Reddit collector implemented (OAuth auth + query + signal mapping)
- `SRC-003`: Hacker News collector implemented (query + signal mapping)
- `SRC-004`: Google Trends collector implemented (region/language query + signal mapping + failure handling)
- `SRC-005`: Product Hunt collector implemented (OAuth + GraphQL + signal mapping)
- `SRC-006`: YouTube collector implemented (search + quota-aware handling + signal mapping)
- `SRC-007`: ingestion runner implemented with retry/timeout policy and per-source error boundaries
- `PRC-001`: signal normalizer implemented (text cleanup, UTC datetime normalization, engagement harmonization)
- `PRC-002`: signal deduplicator implemented (URL/title/topic hash rules + duplicate reason stats)
- `PRC-003`: signal clusterer implemented (canonical topic grouping + deterministic cluster key)
- `PRC-004`: relevance filter implemented (niche/ICP/region/language/include/exclude with reasons)
- `PRC-005`: scoring engine implemented (velocity/volume/engagement/relevance/opinionability, weighted)
- Python workflow standardized on `uv`

## Timeline Logs

- `docs/logs/2026-03-13-session.md`
- `docs/logs/2026-03-16-session.md`
- `docs/logs/2026-03-17-session.md`

## Latest Commit

- `121e35f` - `feat: add topic scorer with configurable weighted components`

## Key Decisions

- Python package manager/runner: `uv` (required)
- No-repeat logic: labels + filters (no suppression window)
- Single-user MVP, no auth in MVP, manual run from UI

## Next Up

- `PRC-006`: explainability output (`why_now`, evidence links, angles)

## Open Risks

- Collector API keys are not configured yet (`.env` values pending)
- Frontend scaffold is still placeholder content (full FE scaffold planned in `FE-001`)
