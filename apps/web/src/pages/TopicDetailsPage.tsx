import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatMetric } from "../components/StatMetric";
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
    <div className="page-content">
      <PageHeader
        eyebrow="Topic"
        title={details?.canonical_topic ?? "Candidate details"}
        subtitle="Drill into why-now rationale, evidence links, and content angles."
        actions={
          <div className="inline-actions">
            <Link to="/shortlist" className="ghost-link">
              Back to shortlist
            </Link>
          </div>
        }
      />

      {state === "loading" ? <LoadingPanel message="Loading details..." /> : null}

      {state === "error" ? (
        <SectionCard title="Topic unavailable">
          <EmptyState title="Cannot load candidate details." detail={errorMessage} />
        </SectionCard>
      ) : null}

      {state === "ready" && details !== null ? (
        <div className="detail-grid">
          <SectionCard title="Summary">
            <div className="stats-grid">
              <StatMetric label="Trend score" value={details.trend_score} />
              <StatMetric
                label="Source coverage"
                value={`${details.source_count} sources / ${details.signal_count} signals`}
              />
              <StatMetric label="Confidence" value={details.confidence ?? "-"} />
            </div>
            <p className="inline-muted">{details.why_now ?? "No why-now summary yet."}</p>
          </SectionCard>

          <SectionCard title="Score breakdown">
            <ul className="kv">
              {Object.entries(details.score_breakdown).map(([key, value]) => (
                <li key={key}>
                  <span>{key}</span>
                  <strong>{value}</strong>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="Evidence">
            {details.evidence_urls.length === 0 ? (
              <EmptyState title="No evidence links available." detail="Run another cycle for more source traces." />
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
          </SectionCard>

          <SectionCard title="Content angles">
            {details.angles.length === 0 ? (
              <EmptyState title="No angles generated yet." detail="Angles will appear after scoring and explanation." />
            ) : (
              <ul className="stack-list">
                {details.angles.map((angle) => (
                  <li key={angle}>{angle}</li>
                ))}
              </ul>
            )}
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}
