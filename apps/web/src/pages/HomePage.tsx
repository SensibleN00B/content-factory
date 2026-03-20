import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingPanel } from "../components/LoadingPanel";
import { PageHeader } from "../components/PageHeader";
import { SectionCard } from "../components/SectionCard";
import { StatMetric } from "../components/StatMetric";
import { StatusBadge } from "../components/StatusBadge";
import {
  getDashboardBriefing,
  getHealthStatus,
  type DashboardBriefingResponse,
  type HealthStatus,
} from "../lib/api";

type HealthState =
  | { status: "loading" }
  | { status: "ready"; payload: HealthStatus }
  | { status: "error"; message: string };

type BriefingState =
  | { status: "loading" }
  | { status: "ready"; payload: DashboardBriefingResponse }
  | { status: "error"; message: string };

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatDropReason(value: string): string {
  return value
    .split("_")
    .map((part) => {
      if (part.length === 0) {
        return part;
      }
      return part[0].toUpperCase() + part.slice(1);
    })
    .join(" ");
}

export function HomePage() {
  const [healthState, setHealthState] = useState<HealthState>({ status: "loading" });
  const [briefingState, setBriefingState] = useState<BriefingState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    getHealthStatus()
      .then((payload) => {
        if (!active) {
          return;
        }
        setHealthState({ status: "ready", payload });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Unexpected error while loading health status";
        setHealthState({ status: "error", message });
      });

    getDashboardBriefing()
      .then((payload) => {
        if (!active) {
          return;
        }
        setBriefingState({ status: "ready", payload });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error
            ? error.message
            : "Unexpected error while loading dashboard briefing";
        setBriefingState({ status: "error", message });
      });

    return () => {
      active = false;
    };
  }, []);

  const briefingUnavailableMessage = useMemo(() => {
    if (briefingState.status === "error") {
      return "AI assessment is currently unavailable.";
    }
    if (briefingState.status !== "ready") {
      return "";
    }
    if (briefingState.payload.briefing_available) {
      return "";
    }
    return briefingState.payload.briefing_unavailable_reason ?? "AI assessment is currently unavailable.";
  }, [briefingState]);

  const briefingItems =
    briefingState.status === "ready" ? briefingState.payload.briefing_items : [];
  const recentTopics = briefingState.status === "ready" ? briefingState.payload.recent_topics : [];
  const pipelineStages =
    briefingState.status === "ready" ? briefingState.payload.pipeline_metrics.stages : [];
  const topDropReasons =
    briefingState.status === "ready"
      ? Object.entries(briefingState.payload.pipeline_metrics.drop_reasons)
          .sort((left, right) => right[1] - left[1])
          .slice(0, 5)
      : [];

  return (
    <div className="page-content">
      <PageHeader
        eyebrow="Discovery"
        title="Discovery Desk"
        subtitle="Track what matters now, review AI briefing insights, and move quickly into action."
        actions={
          <div className="inline-actions">
            <Link to="/runs" className="ghost-link">
              Start run
            </Link>
            <Link to="/shortlist" className="ghost-link">
              Open shortlist
            </Link>
          </div>
        }
      />

      <section className="dashboard-grid">
        <SectionCard
          title="AI Briefing"
          subtitle="LLM synthesis from latest movement and source diagnostics."
          className="dashboard-card-wide"
        >
          {briefingState.status === "loading" ? (
            <LoadingPanel message="Preparing AI briefing..." />
          ) : (
            <div className="briefing-frame">
              <div
                data-testid="ai-briefing-panel"
                className={
                  briefingUnavailableMessage
                    ? "briefing-panel briefing-panel-blurred"
                    : "briefing-panel"
                }
              >
                {briefingItems.length === 0 ? (
                  <EmptyState
                    title="No AI briefing yet."
                    detail="Complete a run to generate a concise AI assessment."
                  />
                ) : (
                  <ul className="briefing-list">
                    {briefingItems.map((item, index) => (
                      <li key={`${item.title}-${index}`}>
                        <strong>{item.title}</strong>
                        <p>{item.detail}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {briefingUnavailableMessage ? (
                <p className="briefing-overlay-message">{briefingUnavailableMessage}</p>
              ) : null}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Recent Topics" subtitle="Latest ranked topics from recent completed runs.">
          {briefingState.status === "loading" ? (
            <LoadingPanel message="Loading recent topics..." />
          ) : recentTopics.length === 0 ? (
            <EmptyState
              title="No recent topics yet."
              detail="Run discovery and shortlist signals to populate this feed."
            />
          ) : (
            <ul className="topic-feed">
              {recentTopics.slice(0, 6).map((topic) => (
                <li key={topic.candidate_id}>
                  <Link to={`/shortlist/${topic.candidate_id}`} className="topic-feed-link">
                    <div>
                      <strong>{topic.canonical_topic}</strong>
                      <p>{topic.why_now ?? "No why-now summary yet."}</p>
                    </div>
                    <div className="topic-feed-meta">
                      <StatusBadge value={topic.movement} />
                      <span>{topic.trend_score.toFixed(1)}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard title="Pipeline Funnel" subtitle="How many signals survive each filtering stage.">
          {briefingState.status === "loading" ? (
            <LoadingPanel message="Loading pipeline diagnostics..." />
          ) : pipelineStages.length === 0 ? (
            <EmptyState
              title="No pipeline metrics yet."
              detail="Pipeline diagnostics appear after at least one completed run."
            />
          ) : (
            <>
              <div className="funnel-list">
                {pipelineStages.map((stage) => (
                  <div key={stage.stage_key} className="funnel-row">
                    <p>{stage.label}</p>
                    <strong>
                      {stage.kept_count} kept / {stage.dropped_count} dropped ({stage.drop_rate}%)
                    </strong>
                  </div>
                ))}
              </div>
              {topDropReasons.length > 0 ? (
                <div className="chip-row" aria-label="Top drop reasons">
                  {topDropReasons.map(([reason, count]) => (
                    <span key={reason} className="chip diagnostic-chip">
                      {formatDropReason(reason)}: {count}
                    </span>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </SectionCard>

        <SectionCard title="Operational Context" subtitle="Quick context for service and run readiness.">
          <div className="stats-grid">
            {healthState.status === "ready" ? (
              <>
                <StatMetric label="API service" value={healthState.payload.service} />
                <StatMetric
                  label="API status"
                  value={healthState.payload.status}
                  tone={healthState.payload.status === "ok" ? "ok" : "error"}
                />
                <StatMetric label="API version" value={healthState.payload.version} />
              </>
            ) : healthState.status === "error" ? (
              <StatMetric label="API health" value="Unavailable" tone="error" />
            ) : (
              <StatMetric label="API health" value="Checking..." />
            )}

            {briefingState.status === "ready" ? (
              <>
                <StatMetric
                  label="Latest run"
                  value={briefingState.payload.latest_run.status}
                  tone={
                    briefingState.payload.latest_run.status === "completed" ? "ok" : "default"
                  }
                />
                <StatMetric
                  label="Candidates"
                  value={briefingState.payload.latest_run.candidate_count}
                />
                <StatMetric
                  label="Generated at"
                  value={formatDateTime(briefingState.payload.generated_at)}
                />
                <StatMetric
                  label="Source health"
                  value={`${briefingState.payload.source_health.healthy_sources}/${briefingState.payload.source_health.total_sources}`}
                  tone={
                    briefingState.payload.source_health.failed_sources > 0 ? "error" : "ok"
                  }
                />
                <StatMetric
                  label="Failed sources"
                  value={briefingState.payload.source_health.failed_sources}
                  tone={
                    briefingState.payload.source_health.failed_sources > 0 ? "error" : "default"
                  }
                />
              </>
            ) : (
              <StatMetric label="Latest run" value="Waiting for dashboard data..." />
            )}
          </div>
          <div className="inline-actions">
            <Link to="/shortlist" className="ghost-link">
              Open shortlist review
            </Link>
          </div>
        </SectionCard>
      </section>
    </div>
  );
}
