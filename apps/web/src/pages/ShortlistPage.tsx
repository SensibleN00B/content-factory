import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getCandidates, type CandidateResponse } from "../lib/api";

type ShortlistState = "idle" | "loading" | "ready" | "error";

function parseLabels(value: string): string[] {
  return value
    .split(/[\n,]/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ShortlistPage() {
  const [state, setState] = useState<ShortlistState>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [runIdInput, setRunIdInput] = useState<string>("");
  const [excludeLabelsInput, setExcludeLabelsInput] = useState<string>("selected_for_post,published");
  const [items, setItems] = useState<CandidateResponse[]>([]);

  const canLoad = useMemo(() => state !== "loading", [state]);

  async function loadCandidates() {
    setState("loading");
    setErrorMessage("");

    try {
      const runId = runIdInput.trim() ? Number(runIdInput.trim()) : undefined;
      const candidates = await getCandidates({
        runId: Number.isFinite(runId ?? NaN) ? runId : undefined,
        excludeLabels: parseLabels(excludeLabelsInput),
      });
      setItems(candidates);
      setState("ready");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to load candidates";
      setErrorMessage(message);
      setState("error");
    }
  }

  return (
    <main className="page">
      <section className="panel settings-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Shortlist</p>
            <h1>Ranked Topic Candidates</h1>
            <p className="subtitle">Review trend score, source coverage, and why-now summary.</p>
          </div>
          <div className="panel-links">
            <Link to="/" className="ghost-link">
              Dashboard
            </Link>
            <Link to="/settings" className="ghost-link">
              Settings
            </Link>
            <Link to="/runs" className="ghost-link">
              Run console
            </Link>
          </div>
        </div>

        <div className="filter-grid">
          <label>
            Run ID (optional)
            <input
              value={runIdInput}
              onChange={(event) => setRunIdInput(event.target.value)}
              placeholder="e.g. 12"
            />
          </label>
          <label>
            Exclude labels (comma/newline)
            <textarea
              value={excludeLabelsInput}
              onChange={(event) => setExcludeLabelsInput(event.target.value)}
              rows={3}
            />
          </label>
        </div>

        <div className="settings-actions">
          <button type="button" onClick={loadCandidates} disabled={!canLoad}>
            {state === "loading" ? "Loading..." : "Load shortlist"}
          </button>
          {state === "error" && <p className="error">{errorMessage}</p>}
          {state === "ready" && <p className="muted">{items.length} topics loaded</p>}
        </div>

        <div className="source-table-wrap">
          <table className="source-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Score</th>
                <th>Sources</th>
                <th>Why now</th>
                <th>Labels</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/shortlist/${item.id}`} className="topic-link">
                      {item.canonical_topic}
                    </Link>
                  </td>
                  <td>{item.trend_score}</td>
                  <td>
                    {item.source_count} sources / {item.signal_count} signals
                  </td>
                  <td>{item.why_now ?? "-"}</td>
                  <td>{item.labels.length ? item.labels.join(", ") : "-"}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    No candidates yet. Start a run, then load shortlist.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
