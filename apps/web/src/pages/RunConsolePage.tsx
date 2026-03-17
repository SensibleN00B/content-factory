import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { createRun, getRun, type RunResponse } from "../lib/api";

type RunUiState = "idle" | "creating" | "polling" | "error";

const ACTIVE_RUN_STATUSES = new Set(["pending", "collecting", "processing", "scoring"]);
const MAX_POLL_ATTEMPTS = 30;

const SOURCE_LABELS: Record<string, string> = {
  google_trends: "Google Trends",
  reddit: "Reddit",
  hackernews: "Hacker News",
  producthunt: "Product Hunt",
  youtube: "YouTube",
};

export function RunConsolePage() {
  const [runState, setRunState] = useState<RunUiState>("idle");
  const [currentRun, setCurrentRun] = useState<RunResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [pollAttempts, setPollAttempts] = useState<number>(0);

  const shouldPoll = useMemo(() => {
    if (currentRun === null) {
      return false;
    }
    return ACTIVE_RUN_STATUSES.has(currentRun.status) && pollAttempts < MAX_POLL_ATTEMPTS;
  }, [currentRun, pollAttempts]);

  useEffect(() => {
    if (!shouldPoll || currentRun === null) {
      return;
    }

    const timer = window.setInterval(() => {
      getRun(currentRun.id)
        .then((freshRun) => {
          setCurrentRun(freshRun);
          setPollAttempts((value) => value + 1);
        })
        .catch((error: unknown) => {
          const message = error instanceof Error ? error.message : "Failed to poll run status";
          setRunState("error");
          setErrorMessage(message);
          window.clearInterval(timer);
        });
    }, 2000);

    return () => {
      window.clearInterval(timer);
    };
  }, [currentRun, shouldPoll]);

  useEffect(() => {
    if (currentRun === null) {
      return;
    }
    if (ACTIVE_RUN_STATUSES.has(currentRun.status) && pollAttempts < MAX_POLL_ATTEMPTS) {
      setRunState("polling");
      return;
    }
    if (runState !== "error") {
      setRunState("idle");
    }
  }, [currentRun, pollAttempts, runState]);

  async function startRun() {
    setRunState("creating");
    setErrorMessage("");
    setPollAttempts(0);

    try {
      const run = await createRun();
      setCurrentRun(run);
      if (ACTIVE_RUN_STATUSES.has(run.status)) {
        setRunState("polling");
      } else {
        setRunState("idle");
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create run";
      setRunState("error");
      setErrorMessage(message);
    }
  }

  async function refreshRun() {
    if (currentRun === null) {
      return;
    }
    try {
      const run = await getRun(currentRun.id);
      setCurrentRun(run);
      setErrorMessage("");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to refresh run";
      setRunState("error");
      setErrorMessage(message);
    }
  }

  return (
    <main className="page">
      <section className="panel settings-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Run Console</p>
            <h1>Manual Trend Discovery Run</h1>
            <p className="subtitle">Trigger run and watch source-level collection states.</p>
          </div>
          <div className="panel-links">
            <Link to="/" className="ghost-link">
              Dashboard
            </Link>
            <Link to="/settings" className="ghost-link">
              Settings
            </Link>
            <Link to="/shortlist" className="ghost-link">
              Shortlist
            </Link>
          </div>
        </div>

        <div className="settings-actions">
          <button type="button" onClick={startRun} disabled={runState === "creating" || runState === "polling"}>
            {runState === "creating" ? "Starting..." : "Start run"}
          </button>
          <button type="button" className="secondary-btn" onClick={refreshRun} disabled={currentRun === null}>
            Refresh
          </button>
          {runState === "polling" && <p className="muted">Polling run status...</p>}
          {runState === "error" && <p className="error">{errorMessage}</p>}
        </div>

        {currentRun === null ? (
          <p className="muted">No run started yet.</p>
        ) : (
          <div className="run-console">
            <div className="run-summary">
              <p>
                Run ID: <strong>{currentRun.id}</strong>
              </p>
              <p>
                Status: <strong className={`status-${currentRun.status}`}>{currentRun.status}</strong>
              </p>
              <p>
                Created: <strong>{new Date(currentRun.created_at).toLocaleString()}</strong>
              </p>
            </div>

            <div className="source-table-wrap">
              <table className="source-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Fetched</th>
                    <th>Duration</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {currentRun.sources.map((source) => (
                    <tr key={source.source}>
                      <td>{SOURCE_LABELS[source.source] ?? source.source}</td>
                      <td>
                        <span className={`status-chip status-${source.status}`}>{source.status}</span>
                      </td>
                      <td>{source.fetched_count}</td>
                      <td>{source.duration_ms ?? "-"}</td>
                      <td>{source.error_text ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pollAttempts >= MAX_POLL_ATTEMPTS && ACTIVE_RUN_STATUSES.has(currentRun.status) && (
              <p className="muted">
                Auto-poll paused after {MAX_POLL_ATTEMPTS} checks. Click Refresh to continue manually.
              </p>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
