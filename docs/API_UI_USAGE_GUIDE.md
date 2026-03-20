# API and UI Usage Guide (MVP)

This guide documents how to operate the current Trend Discovery MVP without extra handholding.

## 1. Quick Start

1. Copy `.env.example` to `.env`.
2. Fill required DB values and source API keys when needed.
3. Start services:
   - `docker compose -f infra/docker-compose.yml up --build -d`
4. Open:
   - API: `http://127.0.0.1:8000`
   - Web: `http://localhost:5173`
5. Verify API:
   - `GET http://127.0.0.1:8000/health`

## 2. Core Workflow (UI)

1. Open `Settings` page (`/settings`) and save profile inputs.
2. Open `Run console` (`/runs`) and click `Start run`.
3. Poll run state until final status.
4. Open `Shortlist` (`/shortlist`) and click `Load shortlist`.
5. Apply labels (`selected_for_post`, `published`, `watchlist`, `not_relevant`).
6. Keep `Only new` enabled to hide already selected/published topics.

## 3. API Reference

Base URL: `http://127.0.0.1:8000`

### Health

- `GET /health`
- Response `200`:

```json
{
  "status": "ok"
}
```

### Profile

- `GET /api/profile`
  - `200`: current profile
  - `404`: profile not initialized
- `PUT /api/profile`
  - Upserts single-user profile

Request body:

```json
{
  "niche": ["AI", "automation"],
  "icp": ["business owners", "CEO", "CTO"],
  "regions": ["US", "CA", "EU"],
  "language": "en",
  "seeds": ["ai agent", "voice ai"],
  "negatives": ["crypto"],
  "settings": {
    "content_types": ["linkedin", "x", "short_video", "carousel"]
  }
}
```

### Runs

- `POST /api/runs`
  - Creates a manual run with input snapshot and source rows (`pending`).
- `GET /api/runs/{run_id}`
  - Returns run status and per-source status.

Run response includes:
- `status`: `pending|collecting|processing|scoring|completed|failed`
- `sources[]`: `source`, `status`, `fetched_count`, `error_text`, `duration_ms`

### Labels

- `GET /api/labels`
- Returns seeded labels:
  - `selected_for_post`
  - `published`
  - `not_relevant`
  - `duplicate`
  - `watchlist`

### Topic Label Actions

- `POST /api/topics/{topic_cluster_id}/labels`
  - Body: `{ "label": "watchlist" }`
  - `201` on create, `200` if already assigned
- `DELETE /api/topics/{topic_cluster_id}/labels/{label_name}`
  - `204` on success

### Candidates

- `GET /api/candidates`
  - Query params:
    - `run_id` (optional)
    - `exclude_labels` (repeatable): e.g. `?exclude_labels=published&exclude_labels=selected_for_post`
- `GET /api/candidates/{candidate_id}`
  - Returns candidate details, score breakdown, evidence links, angles

### Dashboard Briefing

- `GET /api/dashboard/briefing`
  - Returns dashboard-ready briefing data so UI does not compute trend intelligence client-side.
  - Payload includes:
    - `briefing_items[]` (4-5 concise summary bullets)
    - `recent_topics[]` (latest run topics with movement classification)
    - `latest_run` (metadata + candidate count)
    - `pipeline_metrics` (stage-by-stage kept/dropped/drop_rate + drop reasons)
    - `source_health` (healthy/failed source counts)
  - Summarization mode:
    - `BRIEFING_SUMMARIZER_MODE=llm`: uses OpenAI Responses API when `OPENAI_API_KEY` is set.
    - If provider fails or key is missing, API returns unavailable state:
      - `briefing_available=false`
      - `briefing_unavailable_reason` with explanation
  - Performance behavior:
    - Dashboard read path does not wait for a live LLM call.
    - LLM briefing is cached by latest completed run.
    - Cache refresh runs after a new discovery run completes.

## 4. Operational Notes

- No auth in MVP (single-user mode).
- Run scheduling is manual in MVP.
- No-repeat behavior is label-based via `exclude_labels`.
- Logging is structured JSON (controlled by `LOG_LEVEL` and `LOG_JSON`).
- Dashboard should consume `/api/dashboard/briefing` directly, not derive briefing from raw candidate lists.

## 5. Common Errors

- `404 Profile is not initialized`
  - Open Settings page and save profile first.
- `404 Run not found`
  - Verify `run_id`.
- `404 Topic cluster not found`
  - Candidate/topic may be stale or filtered from current run.
- Empty shortlist
  - Check run status and source errors in run console.

## 6. Useful Commands

- Format: `pwsh ./scripts/format.ps1`
- Lint: `pwsh ./scripts/lint.ps1`
- Test: `pwsh ./scripts/test.ps1`
- Backend tests only: `uv run --project apps/api --group dev pytest apps/api/tests`
