# MVP Release Checklist

Use this checklist before tagging or sharing an MVP build.

## 1. Environment and Secrets

- `.env` exists and required fields are set.
- Database is reachable.
- Source credentials are configured for enabled collectors.

## 2. Quality Gates

- Backend tests pass.
- Frontend tests pass.
- Lint is clean for backend and frontend.
- Recent manual UI sanity check completed:
  - Settings save
  - Run trigger
  - Shortlist load
  - Label add/remove

## 3. Release Smoke Command

Run one command from repo root:

```powershell
pwsh ./scripts/smoke.ps1
```

If Docker services are not running yet, either start them first or run:

```powershell
pwsh ./scripts/smoke.ps1 -SkipDockerChecks
```

## 4. Service Checks

- `GET /health` returns `200`.
- Web app root returns `200`.
- `GET /api/labels` returns seeded labels.

## 5. Documentation Checks

- `docs/LOCAL_SETUP_AND_TESTING.md` is up to date.
- `docs/API_UI_USAGE_GUIDE.md` is up to date.
- `docs/logs/CURRENT_STATUS.md` reflects current ticket state.

## 6. Go/No-Go Decision

- Go: all checks green, no open blocker defects.
- No-Go: any failing quality gate or missing critical secrets/config.
