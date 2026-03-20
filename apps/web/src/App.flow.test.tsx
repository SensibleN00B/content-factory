import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("App integration flow", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === "string" ? input : input.toString();
        const method = init?.method ?? "GET";

        if (url.endsWith("/health") && method === "GET") {
          return jsonResponse({ service: "api", status: "ok", version: "0.1.0" });
        }

        if (url.endsWith("/api/dashboard/briefing") && method === "GET") {
          return jsonResponse({
            generated_at: "2026-03-20T12:00:00Z",
            briefing_available: true,
            briefing_unavailable_reason: null,
            briefing_items: [
              {
                kind: "rising",
                title: "Clinic workflow automation is accelerating",
                detail: "Topic strength increased across recent runs with broader source coverage.",
              },
              {
                kind: "new",
                title: "Voice AI demand is entering new segments",
                detail: "New topic movement appeared in the latest run.",
              },
              {
                kind: "review_first",
                title: "Review-first focus",
                detail: "AI workflow for clinics remains the highest-priority cluster.",
              },
              {
                kind: "stable",
                title: "Source health remains serviceable",
                detail: "Most connectors returned healthy signal batches.",
              },
            ],
            recent_topics: [
              {
                candidate_id: 11,
                run_id: 1,
                canonical_topic: "AI workflow for clinics",
                trend_score: 88.5,
                movement: "rising",
                why_now: "Strong velocity and relevance",
                source_count: 3,
                signal_count: 4,
                labels: [],
                created_at: "2026-03-17T10:00:00Z",
              },
            ],
            latest_run: {
              id: 1,
              status: "completed",
              created_at: "2026-03-17T10:00:00Z",
              candidate_count: 1,
            },
            pipeline_metrics: {
              stages: [
                {
                  stage_key: "collected",
                  label: "Collected",
                  input_count: 100,
                  kept_count: 100,
                  dropped_count: 0,
                  drop_rate: 0,
                },
                {
                  stage_key: "shortlisted",
                  label: "Shortlisted",
                  input_count: 20,
                  kept_count: 8,
                  dropped_count: 12,
                  drop_rate: 60,
                },
              ],
              drop_reasons: {
                duplicate_url: 5,
              },
            },
            source_health: {
              total_sources: 5,
              healthy_sources: 4,
              failed_sources: 1,
            },
          });
        }

        if (url.endsWith("/api/profile") && method === "GET") {
          return new Response(JSON.stringify({ detail: "Profile is not initialized" }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.endsWith("/api/profile") && method === "PUT") {
          const body = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
          return jsonResponse({
            id: 1,
            created_at: "2026-03-17T10:00:00Z",
            niche: body.niche ?? [],
            icp: body.icp ?? [],
            regions: body.regions ?? [],
            language: body.language ?? "en",
            seeds: body.seeds ?? [],
            negatives: body.negatives ?? [],
            settings: body.settings ?? {},
          });
        }

        if (url.endsWith("/api/runs") && method === "POST") {
          return jsonResponse({
            id: 1,
            profile_id: 1,
            status: "pending",
            started_at: null,
            finished_at: null,
            input_snapshot: null,
            error_summary: null,
            created_at: "2026-03-17T10:00:00Z",
            sources: [
              {
                source: "google_trends",
                status: "pending",
                fetched_count: 0,
                error_text: null,
                duration_ms: null,
                created_at: "2026-03-17T10:00:00Z",
              },
            ],
          });
        }

        if (url.endsWith("/api/runs/1") && method === "GET") {
          return jsonResponse({
            id: 1,
            profile_id: 1,
            status: "completed",
            started_at: null,
            finished_at: null,
            input_snapshot: null,
            error_summary: null,
            created_at: "2026-03-17T10:00:00Z",
            sources: [
              {
                source: "google_trends",
                status: "completed",
                fetched_count: 12,
                error_text: null,
                duration_ms: 100,
                created_at: "2026-03-17T10:00:00Z",
              },
            ],
          });
        }

        if (url.includes("/api/candidates") && method === "GET") {
          if (url.endsWith("/api/candidates/11")) {
            return jsonResponse({
              id: 11,
              run_id: 1,
              topic_cluster_id: 101,
              canonical_topic: "AI workflow for clinics",
              source_count: 3,
              signal_count: 4,
              trend_score: 88.5,
              why_now: "Strong velocity and relevance",
              labels: [],
              created_at: "2026-03-17T10:00:00Z",
              score_breakdown: {
                source_quality: 29,
                momentum: 34,
                audience_fit: 25.5,
              },
              evidence_urls: ["https://example.com/evidence"],
              angles: ["How clinics can deploy AI workflow automation in under 14 days"],
              confidence: 0.91,
            });
          }

          return jsonResponse([
            {
              id: 11,
              run_id: 1,
              topic_cluster_id: 101,
              canonical_topic: "AI workflow for clinics",
              source_count: 3,
              signal_count: 4,
              trend_score: 88.5,
              why_now: "Strong velocity and relevance",
              labels: [],
              created_at: "2026-03-17T10:00:00Z",
            },
          ]);
        }

        if (url.endsWith("/api/topics/101/labels") && method === "POST") {
          return jsonResponse({
            topic_cluster_id: 101,
            label: "watchlist",
            created_at: "2026-03-17T10:00:00Z",
          });
        }

        throw new Error(`Unhandled request: ${method} ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("completes settings -> run -> shortlist -> label flow", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Discovery Inputs" });
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await screen.findByText("Saved.");

    await user.click(screen.getByRole("link", { name: "Run Console" }));
    await screen.findByRole("heading", { name: "Manual Trend Discovery Run" });
    await user.click(screen.getByRole("button", { name: "Start run" }));
    await screen.findByText("Run status");
    await screen.findByText("Source completion");

    await user.click(screen.getByRole("link", { name: "Shortlist" }));
    await screen.findByRole("heading", { name: "Ranked Topic Candidates" });
    await user.click(screen.getByRole("button", { name: "Load shortlist" }));
    await screen.findByText("AI workflow for clinics");
    await screen.findByText("Topic candidates");

    await user.click(screen.getByRole("button", { name: "+watchlist" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "watchlist ×" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("link", { name: "AI workflow for clinics" }));
    await screen.findByText("Score breakdown");
    expect(screen.getByText("Evidence")).toBeInTheDocument();
    expect(screen.getByText("Content angles")).toBeInTheDocument();
  });

  it("renders app shell and discovery dashboard sections", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByRole("navigation", { name: "Primary" });
    expect(screen.getByRole("link", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Discovery Desk" })).toBeInTheDocument();
    expect(screen.getByText("AI Briefing")).toBeInTheDocument();
    expect(screen.getByText("Pipeline Funnel")).toBeInTheDocument();
    expect(screen.getByText("Duplicate Url: 5")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /AI workflow for clinics/i })).toHaveAttribute(
      "href",
      "/shortlist/11",
    );
  });

  it("renders grouped settings sections", async () => {
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Discovery Inputs" });
    expect(screen.getByText("Discovery profile")).toBeInTheDocument();
    expect(screen.getByText("Target audience")).toBeInTheDocument();
  });

  it("keeps AI briefing card visible in unavailable mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === "string" ? input : input.toString();
        const method = init?.method ?? "GET";

        if (url.endsWith("/health") && method === "GET") {
          return jsonResponse({ service: "api", status: "ok", version: "0.1.0" });
        }

        if (url.endsWith("/api/dashboard/briefing") && method === "GET") {
          return jsonResponse(
            {
              detail: "temporary provider error",
            },
            503,
          );
        }

        throw new Error(`Unhandled request: ${method} ${url}`);
      }),
    );

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByText("AI assessment is currently unavailable.");
    expect(screen.getByTestId("ai-briefing-panel")).toHaveClass("briefing-panel-blurred");
  });
});
