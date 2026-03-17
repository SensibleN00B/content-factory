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

    await user.click(screen.getByRole("link", { name: "Run console" }));
    await screen.findByRole("heading", { name: "Manual Trend Discovery Run" });
    await user.click(screen.getByRole("button", { name: "Start run" }));
    await screen.findByText(/Run ID:/);

    await user.click(screen.getByRole("link", { name: "Shortlist" }));
    await screen.findByRole("heading", { name: "Ranked Topic Candidates" });
    await user.click(screen.getByRole("button", { name: "Load shortlist" }));
    await screen.findByText("AI workflow for clinics");

    await user.click(screen.getByRole("button", { name: "+watchlist" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "watchlist ×" })).toBeInTheDocument();
    });
  });
});
