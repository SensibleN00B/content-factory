# Frontend Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the current MVP frontend into a restrained, modern, professional product UI with a discovery-first information architecture and an AI-powered dashboard briefing.

**Architecture:** Keep the current React + Vite + React Router stack, but move from flat page-level screens to a shared app shell and a workflow-led information architecture. The new primary entry point is a `Discovery Desk` dashboard with an `AI Briefing` card, recent topics, and operational context; deeper pages continue to handle setup, runs, shortlist review, and topic drill-down. This plan depends on a dedicated backend briefing payload described in `docs/plans/2026-03-20-dashboard-ai-briefing-backend-plan.md`.

**Tech Stack:** React 19, React Router 7, TypeScript, Vite 8, Vitest, plain CSS.

---

## Current State Snapshot

- Strengths:
  - Core product flow already exists end-to-end: profile setup, run trigger, shortlist review, topic details.
  - API access is centralized in `apps/web/src/lib/api.ts`.
  - A working integration flow test already covers the main happy path in `apps/web/src/App.flow.test.tsx`.
- Structural gaps:
  - Routing is flat and page-level only; there is no shared application shell in `apps/web/src/App.tsx`.
  - Most UI is page-local markup repeated across files (`panel-head`, `panel-links`, action bars, tables).
  - Visual rules live in one global stylesheet (`apps/web/src/styles.css`), which makes reuse and page differentiation hard.
- UX gaps:
  - The home page still reads like a scaffold, not a real dashboard.
  - The current entry point does not help a user understand what matters now without opening raw lists and tables.
  - Settings is a raw textarea form with little grouping, no helper copy, and a weak sense of priority.
  - Run Console and Shortlist depend on generic tables, so the interface feels operationally correct but visually generic.
  - Loading and error states are technically present but not designed as first-class product states.
- Visual gaps:
  - The current pastel glass treatment is pleasant but too soft and generic for a professional analytics product.
  - Typography is functional, but the hierarchy does not feel intentional enough for a premium product.
  - Mobile responsiveness exists only at a basic breakpoint level.

## Recommended Direction

### Option 1: Discovery Desk IA Reboot on Current Stack

Keep React, Router, Vitest, and plain CSS. Add a shared shell, a dashboard-first information architecture, reusable primitives, and redesign the existing pages around `Dashboard -> Discover -> Review -> Topic`.

Why this is the recommended option:

- Lowest delivery risk.
- Preserves the current stack while improving navigation purpose and route hierarchy.
- Gives a large visual/UX gain without a library migration.
- Keeps focus on product quality instead of framework churn.
- Creates a natural home for the new 4-5 item `AI Briefing`.

### Option 2: Add a Component Library During the Redesign

Adopt a UI system such as shadcn or another component stack while redesigning the pages.

Trade-offs:

- Better primitives out of the box.
- Higher migration cost, more decisions, and more room for inconsistency while the app is still small.

### Option 3: Full Product-Surface Expansion

Add new routes, historical reporting, and a larger analytics surface before redesigning the current screens.

Trade-offs:

- Highest long-term upside.
- Too much scope for the next step because the product still needs a stronger core dashboard first.

## Visual Direction

Use an "editorial analytics" direction:

- Light interface with warm neutrals, ink text, steel/teal accents, and restrained depth.
- Stronger visual hierarchy with expressive headings and highly readable body copy.
- Recommended typography pair:
  - Headings: `Newsreader`
  - UI/body: `Source Sans 3`
- Replace the current soft glass look with cleaner surfaces, thinner borders, quieter shadows, and more deliberate spacing.
- Keep motion subtle:
  - page entrance
  - card reveal
  - hover/focus transitions
- Avoid dark-mode-first styling, oversized gradients, or novelty effects that fight the product's analytical purpose.

## Updated Information Architecture

- Primary entry point: `Discovery Desk`
- Supporting pages:
  - `Settings`
  - `Run Console`
  - `Shortlist`
  - `Topic Details`
- Dashboard content order:
  - `AI Briefing`
  - `Recent Topics`
  - `Pipeline Funnel`
  - last run and source health context
  - quick actions
- Dashboard purpose:
  - Let a user understand the main story in 15 seconds.
  - Surface 4-5 synthesized briefing bullets based on recent runs and candidate movement.
  - Make recent topic exploration the visual center of the product.

## Backend Dependency

- Frontend dashboard work depends on a dedicated backend briefing surface.
- See: `docs/plans/2026-03-20-dashboard-ai-briefing-backend-plan.md`
- Required phase-1 backend payload:
  - `briefing_available` boolean and `briefing_unavailable_reason` nullable string for UI state control
  - `briefing_items[]` with 4-5 concise bullets
  - `recent_topics[]` for the dashboard feed
  - `pipeline_metrics` for stage-by-stage filtering visibility:
    - `stages[]` with `stage_key`, `label`, `input_count`, `kept_count`, `dropped_count`, `drop_rate`
    - `drop_reasons` map with aggregated reason counters for diagnostics chips
  - `latest_run` summary
  - `source_health` summary
- The frontend should not infer rising/cooling states from raw lists on its own.
- The frontend should not calculate drop metrics from raw entities on its own; it renders backend-provided `pipeline_metrics`.
- The frontend should not generate synthetic briefing bullets when AI output is unavailable; it should render an unavailable state.

## Implementation Sequence

### Task 1: Establish the Design Foundation and App Shell

**Files:**
- Create: `apps/web/src/components/AppShell.tsx`
- Create: `apps/web/src/components/PageHeader.tsx`
- Create: `apps/web/src/components/AppNav.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write the failing navigation-shell test**

Add assertions that the primary app navigation stays visible and that the shared shell can support a dashboard-first entry point.

```tsx
expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- src/App.flow.test.tsx`
Expected: FAIL because there is no shared shell or primary navigation landmark yet.

**Step 3: Implement the shell and token cleanup**

- Nest the existing routes inside a shared `AppShell`.
- Move repeated header/nav markup out of page files.
- Make `Dashboard` the primary top-level nav label and visual home of the app.
- Replace the current broad pastel/glass styling with tokens for:
  - background
  - surface
  - text
  - muted text
  - border
  - accent
  - success
  - danger
  - shadow
- Add a consistent content width, page spacing, and top-level navigation rhythm.

**Step 4: Run verification**

Run:
- `npm --prefix apps/web test -- src/App.flow.test.tsx`
- `npm --prefix apps/web run build`

Expected:
- PASS for the updated flow test.
- PASS for the production build.

**Step 5: Commit**

```bash
git add apps/web/src/App.tsx apps/web/src/main.tsx apps/web/src/styles.css apps/web/src/components/AppShell.tsx apps/web/src/components/PageHeader.tsx apps/web/src/components/AppNav.tsx apps/web/src/App.flow.test.tsx
git commit -m "feat: add shared app shell and design tokens"
```

### Task 2: Extract Reusable UI Primitives for Product States

**Files:**
- Create: `apps/web/src/components/SectionCard.tsx`
- Create: `apps/web/src/components/StatusBadge.tsx`
- Create: `apps/web/src/components/EmptyState.tsx`
- Create: `apps/web/src/components/LoadingPanel.tsx`
- Create: `apps/web/src/components/StatMetric.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write a failing test for reusable product states**

Add assertions that loading, empty, and status UI are rendered through reusable primitives instead of ad hoc page text.

```tsx
expect(screen.getByText("No candidates yet.")).toBeInTheDocument();
expect(screen.getByText("Start a run, then load shortlist.")).toBeInTheDocument();
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- src/App.flow.test.tsx`
Expected: FAIL after the new assertions because the pages still use page-local fallback markup.

**Step 3: Implement the primitives**

- Create reusable wrappers for cards, status chips, metrics, empty states, and loading blocks.
- Standardize status color mapping for `pending`, `collecting`, `processing`, `scoring`, `completed`, and failure states.
- Use these primitives on at least Home, Run Console, Shortlist, and Topic Details.

**Step 4: Run verification**

Run:
- `npm --prefix apps/web test -- src/App.flow.test.tsx`
- `npm --prefix apps/web run build`

Expected:
- PASS for updated state rendering.
- PASS for the production build.

**Step 5: Commit**

```bash
git add apps/web/src/styles.css apps/web/src/components/SectionCard.tsx apps/web/src/components/StatusBadge.tsx apps/web/src/components/EmptyState.tsx apps/web/src/components/LoadingPanel.tsx apps/web/src/components/StatMetric.tsx apps/web/src/App.flow.test.tsx
git commit -m "feat: add reusable ui primitives for product states"
```

### Task 3: Redesign the Dashboard and Settings Experience

**Files:**
- Modify: `apps/web/src/pages/HomePage.tsx`
- Modify: `apps/web/src/pages/SettingsPage.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write failing tests for the new page hierarchy**

Add assertions that the dashboard presents a real discovery desk with an AI briefing and that settings is grouped into clear sections.

```tsx
expect(screen.getByRole("heading", { name: "Discovery Desk" })).toBeInTheDocument();
expect(screen.getByText("AI Briefing")).toBeInTheDocument();
expect(screen.getByText("Pipeline Funnel")).toBeInTheDocument();
expect(screen.getByText("Discovery profile")).toBeInTheDocument();
expect(screen.getByText("Target audience")).toBeInTheDocument();
expect(screen.getByText("AI assessment is currently unavailable.")).toBeInTheDocument();
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- src/App.flow.test.tsx`
Expected: FAIL because the current pages do not expose the new grouped structure.

**Step 3: Implement the dashboard and settings redesign**

- Dashboard:
  - Replace scaffold copy with a discovery-first product layout.
  - Add an `AI Briefing` card with 4-5 concise bullets from the backend.
  - Add explicit `AI Briefing` state handling:
    - `briefing_available=true`: render bullets normally
    - `briefing_available=false`: blur the briefing block and show a centered message from `briefing_unavailable_reason`
    - fetch error: blur the briefing block and show `AI assessment is currently unavailable.`
  - Keep the unavailable-state rendering inside the same card layout (no route-level fallback page and no layout shift).
  - Do not compute or fabricate fallback briefing bullets on the client.
  - Add a `Recent Topics` feed as the main content area.
  - Add a `Pipeline Funnel` diagnostics card:
    - show stages `Collected -> Normalized -> Deduplicated -> Relevance Passed -> Clustered -> Shortlisted`
    - show `kept`, `dropped`, and `drop_rate` for each stage
    - show top drop-reason chips from `drop_reasons`
    - keep read-only rendering logic in UI, no stage math on client
  - Add compact operational context for:
    - latest run
    - source health
    - shortlist entry point
  - Make the homepage the clear product starting point rather than a generic control panel.
- Settings:
  - Group fields into clear sections.
  - Add helper text under each section.
  - Convert the form from a long raw stack into a guided workflow.
  - Preserve the existing payload shape and save behavior.
- Error states:
  - Keep navigation visible even when data fetches fail.
  - Present failures inside designed cards, not as a stripped-down fallback page.
  - For AI briefing failures specifically, keep the card visible in blurred mode with unavailable messaging.

**Step 4: Run verification**

Run:
- `npm --prefix apps/web test -- src/App.flow.test.tsx`
- `npm --prefix apps/web run build`

Expected:
- PASS for the updated route flow.
- PASS for the production build.

**Step 5: Commit**

```bash
git add apps/web/src/pages/HomePage.tsx apps/web/src/pages/SettingsPage.tsx apps/web/src/lib/api.ts apps/web/src/styles.css apps/web/src/App.flow.test.tsx
git commit -m "feat: redesign discovery dashboard and settings flow"
```

### Task 4: Redesign Run Console and Shortlist as an Analysis Workspace

**Files:**
- Modify: `apps/web/src/pages/RunConsolePage.tsx`
- Modify: `apps/web/src/pages/ShortlistPage.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write failing tests for the new workspace signals**

Add assertions for summary metrics, filter toolbar language, and clearer shortlist actions.

```tsx
expect(screen.getByText("Run status")).toBeInTheDocument();
expect(screen.getByText("Topic candidates")).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Load shortlist" })).toBeInTheDocument();
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- src/App.flow.test.tsx`
Expected: FAIL because the current pages do not expose these redesigned sections yet.

**Step 3: Implement the workspace redesign**

- Run Console:
  - Add a summary row with run ID, lifecycle status, created time, and source completion count.
  - Turn the source table into a more readable operational board with stronger status emphasis.
  - Make the polling state visible but calm.
- Shortlist:
  - Add a persistent filter/action toolbar.
  - Improve scanability of score, source coverage, why-now, and labels.
  - Keep the table if it remains the best density trade-off, but redesign it with stronger spacing, sticky headers, and clearer row actions.
  - Introduce bulk-selection hooks only if they do not threaten delivery scope; otherwise leave a clear layout seam for them.

**Step 4: Run verification**

Run:
- `npm --prefix apps/web test -- src/App.flow.test.tsx`
- `npm --prefix apps/web run build`

Expected:
- PASS for the updated flow test.
- PASS for the production build.

**Step 5: Commit**

```bash
git add apps/web/src/pages/RunConsolePage.tsx apps/web/src/pages/ShortlistPage.tsx apps/web/src/styles.css apps/web/src/App.flow.test.tsx
git commit -m "feat: redesign run console and shortlist workspace"
```

### Task 5: Upgrade Topic Details and Responsive Quality

**Files:**
- Modify: `apps/web/src/pages/TopicDetailsPage.tsx`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write the failing detail-layout test**

Add assertions for a clearer summary section and drill-down structure.

```tsx
expect(screen.getByText("Score breakdown")).toBeInTheDocument();
expect(screen.getByText("Evidence")).toBeInTheDocument();
expect(screen.getByText("Content angles")).toBeInTheDocument();
```

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- src/App.flow.test.tsx`
Expected: FAIL until the page exposes the updated content model and labels.

**Step 3: Implement the detail-page redesign**

- Add breadcrumb or back-navigation clarity.
- Present summary metrics first, then evidence, then angle generation output.
- Make long URLs and dense lists easier to scan.
- Improve responsive behavior for:
  - narrow mobile screens
  - medium tablet widths
  - wide desktop tables and cards
- Ensure hover, focus, and keyboard states are visually explicit.

**Step 4: Run verification**

Run:
- `npm --prefix apps/web test -- src/App.flow.test.tsx`
- `npm --prefix apps/web run build`

Expected:
- PASS for the updated detail structure.
- PASS for the production build.

**Step 5: Commit**

```bash
git add apps/web/src/pages/TopicDetailsPage.tsx apps/web/src/styles.css apps/web/src/App.flow.test.tsx
git commit -m "feat: refine topic details and responsive behavior"
```

### Task 6: Final QA, Local Environment Fixes, and Visual Verification

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `.env.example`
- Modify: `docs/API_UI_USAGE_GUIDE.md`
- Test: `apps/web/src/App.flow.test.tsx`

**Step 1: Write the failing local-config expectation**

Document and verify that local frontend work should not depend on a `localhost` versus `127.0.0.1` mismatch.

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
```

**Step 2: Run existing verification**

Run:
- `npm --prefix apps/web test`
- `npm --prefix apps/web run build`

Expected:
- PASS for all frontend tests.
- PASS for the production build.

**Step 3: Implement the local-dev cleanup**

- Normalize the default local API host to avoid accidental cross-origin friction during visual audits.
- Update `.env.example` so frontend developers know which variable to set.
- Update the UI usage guide with the expected web and API origins for local work.

**Step 4: Run browser verification**

Run a visual pass at:
- `375px`
- `768px`
- `1280px`

Check:
- navigation visibility
- loading states
- empty states
- hover/focus clarity
- table overflow behavior
- route-to-route consistency
- AI briefing blur state readability (desktop and mobile)
- AI briefing unavailable message visibility and contrast

**Step 5: Commit**

```bash
git add apps/web/src/lib/api.ts .env.example docs/API_UI_USAGE_GUIDE.md apps/web/src/App.flow.test.tsx
git commit -m "chore: finalize frontend refresh verification and local config"
```

## Delivery Notes

- Do not migrate to a UI library in this pass.
- Do not ask the frontend to compute briefing intelligence from raw candidate lists.
- The dashboard should consume a dedicated backend payload for briefing and recent-topic context.
- Prefer extraction only where reuse is obvious across at least two pages.
- Keep the product light-themed first; dark mode can be a future iteration.
- Preserve the existing deep links where practical, but allow top-level navigation labels and route purpose to be reframed around the new dashboard-first IA.

## Success Criteria

- The app feels like a professional product, not a scaffold.
- The dashboard is the obvious home screen and gives a user the main story in 15 seconds.
- The `AI Briefing` communicates 4-5 useful takeaways without forcing the user into raw data first.
- If AI briefing is unavailable, the same card remains visible, blurred, and clearly labeled as temporarily unavailable.
- Every route shares one coherent visual system and navigation shell.
- Settings, Run Console, Shortlist, and Topic Details feel like one workflow.
- Empty, loading, success, and error states are designed, not incidental.
- Mobile and desktop both feel intentional.
