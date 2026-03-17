import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getCandidateDetails, type CandidateDetailResponse } from "../lib/api";

type DetailsState = "loading" | "ready" | "error";

export function TopicDetailsPage() {
  const params = useParams<{ candidateId: string }>();
  const candidateId = Number(params.candidateId);
  const [state, setState] = useState<DetailsState>("loading");
  const [details, setDetails] = useState<CandidateDetailResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    if (!Number.isFinite(candidateId) || candidateId <= 0) {
      setState("error");
      setErrorMessage("Invalid candidate id");
      return;
    }

    let active = true;
    getCandidateDetails(candidateId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDetails(payload);
        setState("ready");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Failed to load candidate details";
        setErrorMessage(message);
        setState("error");
      });

    return () => {
      active = false;
    };
  }, [candidateId]);

  return (
    <main className="page">
      <section className="panel settings-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Topic Details</p>
            <h1>{details?.canonical_topic ?? "Candidate details"}</h1>
            <p className="subtitle">Evidence links, score breakdown, and content angles.</p>
          </div>
          <div className="panel-links">
            <Link to="/shortlist" className="ghost-link">
              Shortlist
            </Link>
            <Link to="/runs" className="ghost-link">
              Run console
            </Link>
          </div>
        </div>

        {state === "loading" && <p className="muted">Loading details...</p>}
        {state === "error" && <p className="error">{errorMessage}</p>}

        {state === "ready" && details !== null && (
          <div className="detail-grid">
            <section className="health-card">
              <h2>Summary</h2>
              <ul className="kv">
                <li>
                  <span>Trend score</span>
                  <strong>{details.trend_score}</strong>
                </li>
                <li>
                  <span>Source coverage</span>
                  <strong>
                    {details.source_count} sources / {details.signal_count} signals
                  </strong>
                </li>
                <li>
                  <span>Confidence</span>
                  <strong>{details.confidence ?? "-"}</strong>
                </li>
              </ul>
              <p className="subtitle" style={{ marginTop: "12px", marginBottom: 0 }}>
                {details.why_now ?? "No why-now summary yet."}
              </p>
            </section>

            <section className="health-card">
              <h2>Score Breakdown</h2>
              <ul className="kv">
                {Object.entries(details.score_breakdown).map(([key, value]) => (
                  <li key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ul>
            </section>

            <section className="health-card">
              <h2>Evidence Links</h2>
              {details.evidence_urls.length === 0 ? (
                <p className="muted">No evidence links available.</p>
              ) : (
                <ul className="stack-list">
                  {details.evidence_urls.map((url) => (
                    <li key={url}>
                      <a href={url} target="_blank" rel="noreferrer" className="topic-link">
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="health-card">
              <h2>Angles</h2>
              {details.angles.length === 0 ? (
                <p className="muted">No angles generated yet.</p>
              ) : (
                <ul className="stack-list">
                  {details.angles.map((angle) => (
                    <li key={angle}>{angle}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
