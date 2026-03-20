# Dashboard AI Briefing Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a backend API surface that summarizes recent discovery activity into 4-5 briefing bullets plus a recent-topics dashboard payload, so the frontend can render a discovery dashboard without re-computing product intelligence in the browser.

**Architecture:** Build the dashboard briefing on top of existing `runs`, `run_sources`, `topic_clusters`, and `content_candidates` data. Phase 1 computes deterministic aggregates and trend deltas from recent runs, then passes those aggregates through an LLM-backed briefing synthesis layer with retry support. When LLM output is unavailable, the backend returns an explicit unavailable state so the frontend can blur the briefing block and show a message.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, existing app service layer, existing test stack (`pytest`, `TestClient`, in-memory SQLite).

---

## Scope

- New backend endpoint for dashboard briefing data.
- New service layer that:
  - loads recent runs
  - compares candidate/topic activity across runs
  - classifies topics into `rising`, `stable`, `cooling`, or `new`
  - returns 4-5 concise briefing bullets when LLM output is available
  - returns recent topics for dashboard display
  - returns pipeline filtering diagnostics for dashboard funnel visualization
- No schema migration in phase 1 unless implementation proves it is necessary.
- Keep the provider layer explicit:
  - LLM summarizer with retries/backoff as primary path
  - explicit unavailable state for frontend handling when LLM is missing/failing or input is insufficient

## Proposed API Contract

Recommended endpoint:

- `GET /api/dashboard/briefing`

Recommended response shape:

```json
{
  "generated_at": "2026-03-20T12:00:00Z",
  "briefing_available": true,
  "briefing_unavailable_reason": null,
  "briefing_items": [
    {
      "kind": "rising",
      "title": "Clinic workflow automation is accelerating",
      "detail": "Topic strength increased across recent runs with broader source coverage."
    }
  ],
  "recent_topics": [
    {
      "candidate_id": 11,
      "run_id": 7,
      "canonical_topic": "AI workflow for clinics",
      "trend_score": 88.5,
      "movement": "rising",
      "why_now": "Strong velocity and relevance",
      "source_count": 3,
      "signal_count": 4,
      "labels": ["watchlist"],
      "created_at": "2026-03-20T11:45:00Z"
    }
  ],
  "latest_run": {
    "id": 7,
    "status": "completed",
    "created_at": "2026-03-20T11:40:00Z",
    "candidate_count": 12
  },
  "pipeline_metrics": {
    "stages": [
      {
        "stage_key": "collected",
        "label": "Collected",
        "input_count": 180,
        "kept_count": 180,
        "dropped_count": 0,
        "drop_rate": 0.0
      },
      {
        "stage_key": "deduplicated",
        "label": "Deduplicated",
        "input_count": 180,
        "kept_count": 120,
        "dropped_count": 60,
        "drop_rate": 33.33
      },
      {
        "stage_key": "relevance_passed",
        "label": "Relevance Passed",
        "input_count": 120,
        "kept_count": 72,
        "dropped_count": 48,
        "drop_rate": 40.0
      },
      {
        "stage_key": "shortlisted",
        "label": "Shortlisted",
        "input_count": 72,
        "kept_count": 20,
        "dropped_count": 52,
        "drop_rate": 72.22
      }
    ],
    "drop_reasons": {
      "contains_excluded_keyword": 18,
      "language_mismatch": 14,
      "region_mismatch": 9,
      "duplicate_url": 23,
      "duplicate_title": 21,
      "duplicate_topic": 16
    }
  },
  "source_health": {
    "total_sources": 5,
    "healthy_sources": 4,
    "failed_sources": 1
  }
}
```

## Task 1: Add Response Schemas and Router Surface

**Files:**
- Create: `apps/api/src/app/presentation/http/schemas/dashboard.py`
- Create: `apps/api/src/app/presentation/http/routers/dashboard.py`
- Modify: `apps/api/src/app/presentation/http/api.py`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Write the failing API test**

Create a new API test that requests `/api/dashboard/briefing` and asserts the basic payload contract.

```python
response = client.get("/api/dashboard/briefing")
assert response.status_code == 200
body = response.json()
assert "briefing_items" in body
assert "recent_topics" in body
assert "latest_run" in body
assert "pipeline_metrics" in body
```

**Step 2: Run test to verify it fails**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: FAIL with `404 Not Found` or import errors because the route does not exist yet.

**Step 3: Write minimal implementation**

- Add Pydantic response models for:
  - `DashboardBriefingItemOut`
  - `DashboardRecentTopicOut`
  - `DashboardLatestRunOut`
  - `DashboardPipelineStageOut`
  - `DashboardPipelineMetricsOut`
  - `DashboardSourceHealthOut`
  - `DashboardBriefingOut`
- Add a new router module exposing `GET /api/dashboard/briefing`.
- Register the router in `apps/api/src/app/presentation/http/api.py`.
- Return a temporary hardcoded payload by calling a placeholder service function so the route contract exists early.

**Step 4: Run test to verify it passes**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/app/presentation/http/schemas/dashboard.py apps/api/src/app/presentation/http/routers/dashboard.py apps/api/src/app/presentation/http/api.py apps/api/tests/test_dashboard_briefing_api.py
git commit -m "feat: add dashboard briefing api contract"
```

## Task 2: Build Recent-Run Aggregation Queries

**Files:**
- Create: `apps/api/src/app/services/dashboard_briefing.py`
- Modify: `apps/api/src/app/presentation/http/routers/dashboard.py`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Extend the failing test with seeded run history**

Seed at least three runs with overlapping topics and assert the endpoint returns:

- a non-empty recent topic list
- the latest completed run metadata
- source health counts derived from the latest run

```python
assert body["latest_run"]["status"] == "completed"
assert body["latest_run"]["candidate_count"] >= 1
assert len(body["recent_topics"]) >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: FAIL because the placeholder route does not load real DB data.

**Step 3: Write minimal implementation**

- Create a service that loads recent completed runs.
- Join `runs`, `topic_clusters`, `content_candidates`, `topic_label_links`, and `labels` as needed.
- Compute:
  - latest run metadata
  - candidate count for the latest run
  - source health summary from `run_sources`
  - recent topics ordered for dashboard display
- Keep the query surface small and deterministic; phase 1 does not need historical pagination.

**Step 4: Run test to verify it passes**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/app/services/dashboard_briefing.py apps/api/src/app/presentation/http/routers/dashboard.py apps/api/tests/test_dashboard_briefing_api.py
git commit -m "feat: aggregate recent runs for dashboard payload"
```

## Task 3: Add Topic Movement Classification

**Files:**
- Modify: `apps/api/src/app/services/dashboard_briefing.py`
- Modify: `apps/api/src/app/presentation/http/schemas/dashboard.py`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Extend the failing test for movement classification**

Seed repeated topics across multiple runs and assert the service distinguishes between `rising`, `stable`, `cooling`, and `new`.

```python
movements = {item["canonical_topic"]: item["movement"] for item in body["recent_topics"]}
assert movements["AI workflow for clinics"] == "rising"
assert movements["Voice AI for dentists"] in {"stable", "cooling", "new"}
```

**Step 2: Run test to verify it fails**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: FAIL because movement is not part of the payload yet.

**Step 3: Write minimal implementation**

- Compare the same canonical topic across recent runs.
- Use simple deterministic heuristics based on:
  - trend score delta
  - source count delta
  - signal count delta
  - topic appearance frequency in the recent window
- Add a `movement` field to `recent_topics`.
- Keep heuristics explicit and easy to tune.

**Step 4: Run test to verify it passes**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/app/services/dashboard_briefing.py apps/api/src/app/presentation/http/schemas/dashboard.py apps/api/tests/test_dashboard_briefing_api.py
git commit -m "feat: classify dashboard topics by movement"
```

## Task 4: Generate 4-5 Briefing Bullets from Aggregates

**Files:**
- Modify: `apps/api/src/app/services/dashboard_briefing.py`
- Modify: `apps/api/src/app/presentation/http/schemas/dashboard.py`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Extend the failing test for briefing bullets**

Assert the response contains 4-5 concise briefing items and that each item has a stable `kind`, `title`, and `detail`.

```python
assert 4 <= len(body["briefing_items"]) <= 5
assert all("kind" in item for item in body["briefing_items"])
assert all("title" in item for item in body["briefing_items"])
assert all("detail" in item for item in body["briefing_items"])
```

**Step 2: Run test to verify it fails**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: FAIL because no bullet synthesis exists yet.

**Step 3: Write minimal implementation**

- Add a synthesis contract that returns up to 4-5 bullets with stable `kind/title/detail` fields.
- Use canonical briefing kinds:
  - `rising`
  - `stable`
  - `cooling`
  - `new`
  - `review_first`
- Ensure frontend rendering does not depend on synthesis internals.

**Step 4: Run test to verify it passes**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/app/services/dashboard_briefing.py apps/api/src/app/presentation/http/schemas/dashboard.py apps/api/tests/test_dashboard_briefing_api.py
git commit -m "feat: synthesize dashboard briefing bullets"
```

## Task 5: Add Optional LLM Summarizer Behind Configuration

**Files:**
- Create: `apps/api/src/app/services/briefing_summarizer.py`
- Modify: `apps/api/src/app/core/config.py`
- Modify: `.env.example`
- Modify: `apps/api/src/app/services/dashboard_briefing.py`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Extend the failing test for LLM unavailability behavior**

Add a test that verifies the endpoint still works when no AI provider is configured, and returns explicit unavailable state metadata.

```python
response = client.get("/api/dashboard/briefing")
assert response.status_code == 200
assert response.json()["briefing_available"] is False
assert isinstance(response.json()["briefing_unavailable_reason"], str)
assert response.json()["briefing_items"] == []
```

**Step 2: Run test to verify it fails**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: FAIL after adding provider hooks if unavailable-state behavior is missing.

**Step 3: Write minimal implementation**

- Add config fields for briefing summarization, for example:
  - `BRIEFING_SUMMARIZER_MODE=llm`
  - provider credentials only if the repo already standardizes one
- Create a summarizer abstraction:
  - LLM-backed summarizer as the primary implementation
  - retry/backoff logic for transient provider failures
- Keep the router contract unchanged.
- If the provider is missing, fails, or there is not enough data for briefing synthesis, return:
  - `briefing_available=false`
  - `briefing_unavailable_reason=<message>`
  - `briefing_items=[]`

**Step 4: Run test to verify it passes**

Run: `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/src/app/services/briefing_summarizer.py apps/api/src/app/core/config.py .env.example apps/api/src/app/services/dashboard_briefing.py apps/api/tests/test_dashboard_briefing_api.py
git commit -m "feat: add llm summarizer retries and unavailable-state handling"
```

## Task 6: Document and Verify the Frontend Dependency

**Files:**
- Modify: `docs/API_UI_USAGE_GUIDE.md`
- Modify: `docs/logs/CURRENT_STATUS.md`
- Test: `apps/api/tests/test_dashboard_briefing_api.py`

**Step 1: Run targeted verification**

Run:
- `uv run --project apps/api --group dev pytest apps/api/tests/test_dashboard_briefing_api.py -v`
- `uv run --project apps/api --group dev pytest apps/api/tests/test_candidates_api.py apps/api/tests/test_candidate_details_api.py -v`

Expected:
- PASS for the new dashboard briefing tests.
- PASS for adjacent candidate endpoints to prove no regression.

**Step 2: Write minimal docs updates**

- Document the new dashboard endpoint in `docs/API_UI_USAGE_GUIDE.md`.
- Update `docs/logs/CURRENT_STATUS.md` when implementation lands.
- Note that the frontend dashboard consumes this endpoint rather than assembling the briefing client-side.

**Step 3: Commit**

```bash
git add docs/API_UI_USAGE_GUIDE.md docs/logs/CURRENT_STATUS.md
git commit -m "docs: record dashboard briefing backend support"
```

## Delivery Notes

- Phase 1 should work even when LLM is unavailable by returning explicit unavailable state (not synthetic fallback bullets).
- Do not block dashboard delivery on prompt tuning; keep retry behavior predictable.
- Compute truth in backend aggregates first; synthesize language second.
- Keep briefing bullets short enough for a 4-5 item dashboard card.
- Favor robust provider integration over fragile one-shot calls.

## Success Criteria

- `GET /api/dashboard/briefing` returns a stable payload for the dashboard.
- The payload includes recent topic movement labels and either:
  - 4-5 LLM-generated briefing bullets, or
  - explicit unavailable state (`briefing_available=false`).
- The frontend can render a useful dashboard without inspecting raw run data first.
- Missing AI credentials do not break the endpoint and produce explicit unavailable metadata.
