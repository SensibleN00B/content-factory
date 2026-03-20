import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatMetric } from "../components/StatMetric";
import { StatusBadge } from "../components/StatusBadge";
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

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

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

  const completedSourcesCount = useMemo(() => {
    if (currentRun === null) {
      return 0;
    }
    return currentRun.sources.filter((source) => source.status === "completed").length;
  }, [currentRun]);

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
    <div className="page-content">
      <PageHeader
        eyebrow="Operations"
        title="Manual Trend Discovery Run"
        subtitle="Run status, source execution quality, and data collection health."
      />

      <div className="settings-actions">
        <button type="button" onClick={startRun} disabled={runState === "creating" || runState === "polling"}>
          {runState === "creating" ? "Starting..." : "Start run"}
        </button>
        <button type="button" className="secondary-btn" onClick={refreshRun} disabled={currentRun === null}>
          Refresh
        </button>
        {runState === "polling" ? <p className="muted">Polling run status...</p> : null}
        {runState === "error" ? <p className="error">{errorMessage}</p> : null}
      </div>

      {currentRun === null ? (
        <SectionCard title="Run status">
          <EmptyState title="No run started yet." detail="Start a run to populate this operational board." />
        </SectionCard>
      ) : (
        <div className="run-layout">
          <SectionCard title="Run status">
            <div className="stats-grid">
              <StatMetric label="Run ID" value={currentRun.id} />
              <StatMetric label="Lifecycle" value={currentRun.status} />
              <StatMetric label="Created" value={formatDateTime(currentRun.created_at)} />
              <StatMetric
                label="Source completion"
                value={`${completedSourcesCount}/${currentRun.sources.length}`}
              />
            </div>
          </SectionCard>

          <SectionCard title="Sources board">
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
                        <StatusBadge value={source.status} />
                      </td>
                      <td>{source.fetched_count}</td>
                      <td>{source.duration_ms ?? "-"}</td>
                      <td>{source.error_text ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
