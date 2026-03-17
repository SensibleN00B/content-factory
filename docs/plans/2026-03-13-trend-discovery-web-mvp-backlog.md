# Trend Discovery Web MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-user web MVP that discovers and ranks content topics from 5 sources, supports manual curation via labels/filters, and serves results through a frontend UI.

**Architecture:** Modular monolith with clear domain boundaries (`profile`, `ingestion`, `processing`, `scoring`, `curation`, `delivery`). Backend exposes REST API to a React frontend. Collectors are pluggable adapters behind a common interface.

**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, APScheduler (future), React + TypeScript + Vite, TanStack Query, Docker Compose, Pytest, Playwright (frontend e2e).

---

## Scope and Constraints

- Single-user MVP.
- No authentication in MVP (schema should stay auth-ready).
- Manual run from UI.
- 5 sources in MVP: Google Trends, Reddit, Hacker News, Product Hunt, YouTube.
- No-repeat behavior via labels + `exclude_labels` filter (no suppression window).
- Quality first.

## Ticket Format

- **Priority:** `P0` (blocking), `P1` (important), `P2` (nice-to-have)
- **Estimate:** engineering hours (implementation + local verification)
- **Depends On:** ticket IDs that must be completed first

---

## Backlog Tickets

### Foundation

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| ARCH-001 | P0 | 4h | - | Monorepo structure for `apps/api`, `apps/web`, `packages/contracts`, `infra` | Folders created, base README with project map |
| DEV-001 | P0 | 3h | ARCH-001 | Tooling baseline (`.editorconfig`, lint/format scripts, env templates) | Commands run locally and documented |
| OPS-001 | P0 | 4h | ARCH-001 | Docker Compose for API + DB + Web | `docker compose up` starts all services |
| DOC-001 | P0 | 2h | ARCH-001 | Development runbook (`setup`, `run`, `test`) | New contributor can run project via docs only |

### Backend Core

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| BE-001 | P0 | 5h | ARCH-001 | FastAPI app skeleton with layered module structure | Health endpoint, app boots cleanly |
| BE-002 | P0 | 6h | BE-001 | SQLAlchemy + Alembic integration | Initial migration generated and applied |
| BE-003 | P0 | 7h | BE-002 | Core schema: `profiles`, `runs`, `run_sources`, `raw_signals`, `topic_clusters`, `content_candidates`, `labels`, `topic_label_links` | Tables created with indexes and FK constraints |
| BE-004 | P0 | 5h | BE-003 | Profile API (`GET/PUT /api/profile`) with input snapshot support | Profile updates persist and validate correctly |
| BE-005 | P0 | 6h | BE-003 | Run state machine (`pending -> collecting -> processing -> scoring -> completed/failed`) | State transitions validated; invalid transitions rejected |
| BE-006 | P0 | 5h | BE-005 | Run APIs (`POST /api/runs`, `GET /api/runs/{id}`) | Manual run trigger and status polling work |

### Source Ingestion (5 MVP Sources)

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| SRC-001 | P0 | 4h | BE-005 | Source adapter contract (`SourceConnector`) + registry | New source can be plugged by registration only |
| SRC-002 | P0 | 8h | SRC-001 | Reddit collector (auth + query + mapping to RawSignal) | Collector returns normalized raw payload + metadata |
| SRC-003 | P0 | 6h | SRC-001 | Hacker News collector | Collector returns valid signals and source stats |
| SRC-004 | P0 | 8h | SRC-001 | Google Trends collector | Query works for selected regions/language; failures handled |
| SRC-005 | P0 | 8h | SRC-001 | Product Hunt collector | OAuth/token flow and data mapping implemented |
| SRC-006 | P0 | 8h | SRC-001 | YouTube collector | Trending/search-based retrieval with quota-aware behavior |
| SRC-007 | P0 | 5h | SRC-002,SRC-003,SRC-004,SRC-005,SRC-006 | Retry, timeout, and per-source error boundaries | One source failure does not fail entire run |

### Processing and Intelligence

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| PRC-001 | P0 | 6h | SRC-007 | Normalizer (text cleanup, datetime, engagement harmonization) | All source signals transformed into unified shape |
| PRC-002 | P0 | 6h | PRC-001 | Deduplicator (URL/title/topic hash rules) | Duplicate ratio decreases; tests cover major duplicate paths |
| PRC-003 | P0 | 8h | PRC-002 | Clusterer (canonical topic creation) | Similar topics grouped with deterministic cluster key |
| PRC-004 | P0 | 7h | PRC-003,BE-004 | Relevance filter (niche/ICP/region/language/include/exclude) | Irrelevant topics filtered with auditable reasons |
| PRC-005 | P0 | 8h | PRC-004 | Scoring engine (`velocity, volume, engagement, relevance, opinionability`) with configurable weights | Score breakdown stored per candidate |
| PRC-006 | P1 | 6h | PRC-005 | Explainability output (`why_now` + evidence links + angles) | Every candidate includes explanation tied to source evidence |

### Curation (Labels + Filters)

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| CUR-001 | P0 | 4h | BE-003 | Seed label dictionary (`selected_for_post`, `published`, `not_relevant`, `duplicate`, `watchlist`) | Labels are seeded and queryable |
| CUR-002 | P0 | 5h | CUR-001 | Label APIs (`POST /topics/{id}/labels`, `DELETE /topics/{id}/labels/{label}`) | Label add/remove works with audit timestamp |
| CUR-003 | P0 | 5h | CUR-002 | Candidate API filters (`exclude_labels`) | `Only new` and custom exclusions work via API |

### Frontend

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| FE-001 | P0 | 5h | ARCH-001 | React + TypeScript + Vite scaffold, routing, API client | Web app runs and calls health endpoint |
| FE-002 | P0 | 6h | FE-001,BE-004 | Settings page for profile input | User can save niche/ICP/regions/language from UI |
| FE-003 | P0 | 6h | FE-001,BE-006 | Run Console page (manual run + per-source progress) | User can trigger run and see live status |
| FE-004 | P0 | 7h | FE-001,PRC-005 | Shortlist page (score, sources, why-now summary) | 10-20 candidates shown with sorting/filtering |
| FE-005 | P0 | 6h | FE-004,PRC-006 | Topic details page (evidence links + angles) | Candidate details page is complete and consistent |
| FE-006 | P0 | 6h | FE-004,CUR-003 | Label actions + `exclude_labels` UI chips (including preset `Only new`) | Labeled topics disappear under active filters |

### Quality, Testing, and Reliability

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| QA-001 | P0 | 7h | BE-006 | Backend unit tests for domain/use-cases | Critical use-cases covered and passing |
| QA-002 | P0 | 8h | SRC-007,PRC-005 | Collector contract tests and pipeline integration tests | Tests verify run success with fixture data |
| QA-003 | P0 | 6h | FE-006 | Frontend integration/e2e tests for core user flows | Settings -> Run -> Shortlist -> Label flow passes |
| OBS-001 | P1 | 5h | BE-006 | Structured logging and run metrics (`duration`, `source_failures`, `candidate_count`) | Run diagnostics visible and actionable |
| QA-004 | P1 | 6h | FE-006,PRC-006 | Manual quality protocol for 30-50 topics + tuning worksheet | Precision@15 benchmark recorded and weights tuned |

### Documentation and Release

| ID | Priority | Estimate | Depends On | Task | Definition of Done |
|---|---|---:|---|---|---|
| DOC-002 | P0 | 3h | QA-003 | API reference and UI usage guide | Team can run and operate MVP without handholding |
| REL-001 | P0 | 3h | DOC-002,QA-002,QA-003 | MVP release checklist and smoke script | One-command smoke check before release |
| REL-002 | P1 | 2h | REL-001 | Post-release feedback loop checklist | Clear process for score/filter iteration |

---

## Delivery Sequence (Execution Order)

1. `ARCH-001` -> `DEV-001` -> `OPS-001` -> `DOC-001`
2. Backend core: `BE-001` -> `BE-002` -> `BE-003` -> `BE-004` -> `BE-005` -> `BE-006`
3. Ingestion: `SRC-001` -> `SRC-002..SRC-006` -> `SRC-007`
4. Processing: `PRC-001` -> `PRC-002` -> `PRC-003` -> `PRC-004` -> `PRC-005` -> `PRC-006`
5. Curation: `CUR-001` -> `CUR-002` -> `CUR-003`
6. Frontend: `FE-001` -> `FE-002` -> `FE-003` -> `FE-004` -> `FE-005` -> `FE-006`
7. Quality and release: `QA-001` -> `QA-002` -> `QA-003` -> `OBS-001` -> `QA-004` -> `DOC-002` -> `REL-001` -> `REL-002`

---

## Milestone Checkpoints

### Milestone A: Core Backend Ready
- Completed: `BE-001..BE-006`
- Exit criteria: profile saved, manual run can start and track status.

### Milestone B: Data Pipeline Ready
- Completed: `SRC-001..SRC-007`, `PRC-001..PRC-005`
- Exit criteria: run produces ranked candidates with score breakdown.

### Milestone C: UI Curation Ready
- Completed: `FE-001..FE-006`, `CUR-001..CUR-003`
- Exit criteria: user can run, review, label, and hide topics via filters.

### Milestone D: MVP Release Ready
- Completed: `QA-001..QA-004`, `DOC-002`, `REL-001`
- Exit criteria: quality and reliability gates passed.

---

## MVP Quality Gates

- Run success rate >= 95%.
- Top 15 precision >= 70% (manual review protocol).
- Every candidate has source evidence and score breakdown.
- Label filters reliably exclude marked topics in shortlist views.

---

## Post-MVP Backlog (Future)

- FUT-001: Authentication and user/workspace model.
- FUT-002: Scheduler UI (`daily`, `every 3 days`, `weekly`).
- FUT-003: Additional sources from spreadsheet (`news`, `wikipedia`, `arxiv`, `x`, etc.) via registry.
- FUT-004: Delivery channel adapters (Slack/Telegram).
- FUT-005: Auto-tuning score weights from post performance metrics.
