import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  addTopicLabel,
  getCandidates,
  removeTopicLabel,
  type CandidateResponse,
} from "../lib/api";

type ShortlistState = "idle" | "loading" | "ready" | "error";
const ONLY_NEW_LABELS = ["selected_for_post", "published"];
const QUICK_LABEL_ACTIONS = ["selected_for_post", "watchlist", "not_relevant", "published"];

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
  const [onlyNew, setOnlyNew] = useState<boolean>(true);
  const [excludeLabelInput, setExcludeLabelInput] = useState<string>("");
  const [customExcludeLabels, setCustomExcludeLabels] = useState<string[]>([]);
  const [items, setItems] = useState<CandidateResponse[]>([]);

  const effectiveExcludeLabels = useMemo(() => {
    const labels = [...customExcludeLabels];
    if (onlyNew) {
      labels.push(...ONLY_NEW_LABELS);
    }
    return Array.from(new Set(labels));
  }, [customExcludeLabels, onlyNew]);

  const canLoad = useMemo(() => state !== "loading", [state]);

  async function loadCandidates() {
    setState("loading");
    setErrorMessage("");

    try {
      const runId = runIdInput.trim() ? Number(runIdInput.trim()) : undefined;
      const candidates = await getCandidates({
        runId: Number.isFinite(runId ?? NaN) ? runId : undefined,
        excludeLabels: effectiveExcludeLabels,
      });
      setItems(candidates);
      setState("ready");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to load candidates";
      setErrorMessage(message);
      setState("error");
    }
  }

  function addExcludeLabel() {
    const next = parseLabels(excludeLabelInput);
    if (next.length === 0) {
      return;
    }
    setCustomExcludeLabels((current) => {
      const merged = [...current, ...next];
      return Array.from(new Set(merged));
    });
    setExcludeLabelInput("");
  }

  function removeExcludeLabel(label: string) {
    setCustomExcludeLabels((current) => current.filter((item) => item !== label));
  }

  async function handleAddLabel(item: CandidateResponse, label: string) {
    try {
      await addTopicLabel(item.topic_cluster_id, label);
      const shouldHide = effectiveExcludeLabels.includes(label);
      setItems((current) => {
        if (shouldHide) {
          return current.filter((entry) => entry.id !== item.id);
        }
        return current.map((entry) => {
          if (entry.id !== item.id) {
            return entry;
          }
          const labels = Array.from(new Set([...entry.labels, label]));
          return { ...entry, labels };
        });
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to assign label";
      setErrorMessage(message);
      setState("error");
    }
  }

  async function handleRemoveLabel(item: CandidateResponse, label: string) {
    try {
      await removeTopicLabel(item.topic_cluster_id, label);
      setItems((current) =>
        current.map((entry) => {
          if (entry.id !== item.id) {
            return entry;
          }
          return { ...entry, labels: entry.labels.filter((value) => value !== label) };
        }),
      );
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to remove label";
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
            Custom exclude label
            <div className="inline-input">
              <input
                value={excludeLabelInput}
                onChange={(event) => setExcludeLabelInput(event.target.value)}
                placeholder="e.g. watchlist"
              />
              <button type="button" className="secondary-btn" onClick={addExcludeLabel}>
                Add
              </button>
            </div>
          </label>
        </div>

        <div className="chip-row">
          <button
            type="button"
            className={`chip ${onlyNew ? "chip-active" : ""}`}
            onClick={() => setOnlyNew((value) => !value)}
          >
            Only new
          </button>
          {customExcludeLabels.map((label) => (
            <button
              key={label}
              type="button"
              className="chip"
              onClick={() => removeExcludeLabel(label)}
            >
              {label} ×
            </button>
          ))}
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
                <th>Actions</th>
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
                  <td>
                    {item.labels.length === 0 ? (
                      "-"
                    ) : (
                      <div className="chip-row">
                        {item.labels.map((label) => (
                          <button
                            key={`${item.id}-${label}`}
                            type="button"
                            className="chip"
                            onClick={() => handleRemoveLabel(item, label)}
                          >
                            {label} ×
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="chip-row">
                      {QUICK_LABEL_ACTIONS.map((label) => (
                        <button
                          key={`${item.id}-add-${label}`}
                          type="button"
                          className="chip"
                          onClick={() => handleAddLabel(item, label)}
                        >
                          +{label}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
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
