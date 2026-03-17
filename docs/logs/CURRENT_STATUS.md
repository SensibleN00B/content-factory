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
- `PRC-006`: explainability output implemented (`why_now`, evidence links, content angles)
- `CUR-001`: seed label dictionary implemented and queryable via `GET /api/labels`
- `CUR-002`: topic label APIs implemented (`POST /api/topics/{id}/labels`, `DELETE /api/topics/{id}/labels/{label}`)
- `CUR-003`: candidates API implemented with `exclude_labels` filtering
- `FE-001`: React + TypeScript + Vite scaffold implemented with routing and API health client
- `FE-002`: settings page implemented with profile form and `GET/PUT /api/profile` integration
- `FE-003`: run console implemented (`POST /api/runs`, polling `GET /api/runs/{id}`, per-source status)
- `FE-004`: shortlist page implemented (score, sources, why-now summary + label exclusions)
- `FE-005`: topic details page implemented (evidence links, score breakdown, generated angles)
- `FE-006`: shortlist label actions + `exclude_labels` chips implemented (including `Only new`)
- `QA-001`: backend unit/integration tests expanded for critical curation and run-status flows
- `QA-002`: collector contract tests + trend pipeline integration tests with fixture sources
- `QA-003`: frontend integration flow test added for Settings -> Run -> Shortlist -> Label journey
- Python workflow standardized on `uv`

## Timeline Logs

- `docs/logs/2026-03-13-session.md`
- `docs/logs/2026-03-16-session.md`
- `docs/logs/2026-03-17-session.md`

## Latest Commit

- `bcabc42` - `test: add frontend integration flow coverage for core ui journey`

## Key Decisions

- Python package manager/runner: `uv` (required)
- No-repeat logic: labels + filters (no suppression window)
- Single-user MVP, no auth in MVP, manual run from UI

## Next Up

- `OBS-001`: structured logging and run metrics (`duration`, `source_failures`, `candidate_count`)

## Open Risks

- Collector API keys are not configured yet (`.env` values pending)
- Browser-level Playwright e2e is not added yet (current QA-003 is integration test via Vitest)
