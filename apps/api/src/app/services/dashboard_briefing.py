from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.db.models import (
    ContentCandidate,
    Label,
    Run,
    RunSource,
    TopicCluster,
    TopicLabelLink,
)
from app.presentation.http.schemas.dashboard import (
    DashboardBriefingItemOut,
    DashboardBriefingOut,
    DashboardLatestRunOut,
    DashboardPipelineMetricsOut,
    DashboardPipelineStageOut,
    DashboardRecentTopicOut,
    DashboardSourceHealthOut,
)
from app.services.briefing_summarizer import (
    BriefingContext,
    BriefingTopic,
    resolve_briefing_summarizer,
)

_RECENT_RUN_WINDOW = 5
_RECENT_TOPICS_LIMIT = 20
_BRIEFING_TEMPORARILY_UNAVAILABLE = "AI briefing is temporarily unavailable."
_BRIEFING_PREPARING_MESSAGE = "AI briefing is being prepared after the latest completed run."


@dataclass(frozen=True)
class _DashboardProjection:
    generated_at: datetime
    latest_run: DashboardLatestRunOut
    recent_topics: list[DashboardRecentTopicOut]
    pipeline_metrics: DashboardPipelineMetricsOut
    source_health: DashboardSourceHealthOut
    context: BriefingContext


@dataclass(frozen=True)
class _BriefingCacheEntry:
    run_id: int
    generated_at: datetime
    briefing_available: bool
    briefing_unavailable_reason: str | None
    briefing_items: list[DashboardBriefingItemOut]


_BRIEFING_CACHE_BY_RUN: dict[int, _BriefingCacheEntry] = {}
_BRIEFING_CACHE_LOCK = Lock()


def build_dashboard_briefing(*, db_session: Session) -> DashboardBriefingOut:
    projection = _build_latest_dashboard_projection(db_session=db_session)
    if projection is None:
        return _empty_briefing()

    cached_briefing = _get_cached_briefing(run_id=projection.latest_run.id)
    if cached_briefing is not None:
        generated_at = cached_briefing.generated_at
        briefing_available = cached_briefing.briefing_available
        briefing_unavailable_reason = cached_briefing.briefing_unavailable_reason
        briefing_items_out = list(cached_briefing.briefing_items)
    else:
        generated_at = projection.generated_at
        briefing_available = False
        briefing_items_out = []
        briefing_unavailable_reason = (
            _default_unavailable_reason(recent_topics=projection.recent_topics)
            or _BRIEFING_PREPARING_MESSAGE
        )

    return DashboardBriefingOut(
        generated_at=generated_at,
        briefing_available=briefing_available,
        briefing_unavailable_reason=briefing_unavailable_reason,
        briefing_items=briefing_items_out,
        recent_topics=projection.recent_topics,
        latest_run=projection.latest_run,
        pipeline_metrics=projection.pipeline_metrics,
        source_health=projection.source_health,
    )


def refresh_briefing_cache_for_latest_run(*, db_session: Session) -> None:
    projection = _build_latest_dashboard_projection(db_session=db_session)
    if projection is None:
        return

    latest_run_id = projection.latest_run.id
    mode = settings.briefing_summarizer_mode.strip().lower()
    reason = _default_unavailable_reason(recent_topics=projection.recent_topics)
    if reason is not None:
        _set_cached_briefing(
            run_id=latest_run_id,
            briefing_available=False,
            briefing_unavailable_reason=reason,
            briefing_items=[],
        )
        return

    summarizer = resolve_briefing_summarizer(
        mode=mode,
        api_key=settings.openai_api_key,
        model=settings.briefing_summarizer_model,
        base_url=settings.openai_api_base_url,
        timeout_seconds=settings.briefing_summarizer_timeout_seconds,
        max_retries=settings.briefing_summarizer_max_retries,
        retry_backoff_seconds=settings.briefing_summarizer_retry_backoff_seconds,
    )
    try:
        briefing_items = summarizer.summarize(context=projection.context)
        briefing_items_out = [
            DashboardBriefingItemOut(kind=item.kind, title=item.title, detail=item.detail)
            for item in briefing_items
        ]
        _set_cached_briefing(
            run_id=latest_run_id,
            briefing_available=True,
            briefing_unavailable_reason=None,
            briefing_items=briefing_items_out,
        )
    except Exception:
        _set_cached_briefing(
            run_id=latest_run_id,
            briefing_available=False,
            briefing_unavailable_reason=_BRIEFING_TEMPORARILY_UNAVAILABLE,
            briefing_items=[],
        )


def _build_latest_dashboard_projection(*, db_session: Session) -> _DashboardProjection | None:
    recent_runs = list(
        db_session.scalars(
            select(Run)
            .where(Run.status == "completed")
            .order_by(Run.created_at.desc(), Run.id.desc())
            .limit(_RECENT_RUN_WINDOW)
        )
    )
    if not recent_runs:
        return None

    latest_run = recent_runs[0]
    latest_run_id = latest_run.id
    run_ids = [run.id for run in recent_runs]

    candidate_rows = db_session.execute(
        select(ContentCandidate, TopicCluster)
        .join(TopicCluster, TopicCluster.id == ContentCandidate.topic_cluster_id)
        .where(ContentCandidate.run_id.in_(run_ids))
        .order_by(
            ContentCandidate.run_id.desc(),
            ContentCandidate.trend_score.desc(),
            ContentCandidate.id.asc(),
        )
    ).all()

    history_by_topic: dict[str, list[float]] = defaultdict(list)
    latest_rows: list[tuple[ContentCandidate, TopicCluster]] = []
    latest_topic_cluster_ids: list[int] = []

    for candidate, cluster in candidate_rows:
        if candidate.run_id == latest_run_id:
            latest_rows.append((candidate, cluster))
            latest_topic_cluster_ids.append(cluster.id)
        else:
            history_by_topic[cluster.canonical_topic].append(float(candidate.trend_score))

    latest_rows = latest_rows[:_RECENT_TOPICS_LIMIT]
    labels_map = _load_labels_map(db_session=db_session, topic_cluster_ids=latest_topic_cluster_ids)
    recent_topics = [
        _to_recent_topic(
            candidate=candidate,
            cluster=cluster,
            labels=labels_map.get(cluster.id, []),
            movement=_classify_movement(
                current_score=float(candidate.trend_score),
                previous_scores=history_by_topic.get(cluster.canonical_topic, []),
            ),
        )
        for candidate, cluster in latest_rows
    ]

    candidate_count = (
        db_session.scalar(
            select(func.count(ContentCandidate.id)).where(ContentCandidate.run_id == latest_run_id)
        )
        or 0
    )
    source_rows = list(
        db_session.scalars(
            select(RunSource)
            .where(RunSource.run_id == latest_run_id)
            .order_by(RunSource.source.asc())
        )
    )
    source_health = _build_source_health(source_rows=source_rows)
    pipeline_metrics = _build_pipeline_metrics(
        source_rows=source_rows,
        latest_run_id=latest_run_id,
        db_session=db_session,
    )
    context = BriefingContext(
        topics=[
            BriefingTopic(
                canonical_topic=topic.canonical_topic,
                movement=topic.movement,
                trend_score=topic.trend_score,
                source_count=topic.source_count,
                signal_count=topic.signal_count,
            )
            for topic in recent_topics
        ],
        latest_run_id=latest_run_id,
        latest_candidate_count=int(candidate_count),
        total_sources=source_health.total_sources,
        healthy_sources=source_health.healthy_sources,
        failed_sources=source_health.failed_sources,
    )
    return _DashboardProjection(
        generated_at=datetime.now(UTC),
        latest_run=DashboardLatestRunOut(
            id=latest_run.id,
            status=latest_run.status,
            created_at=latest_run.created_at,
            candidate_count=int(candidate_count),
        ),
        recent_topics=recent_topics,
        pipeline_metrics=pipeline_metrics,
        source_health=source_health,
        context=context,
    )


def _empty_briefing() -> DashboardBriefingOut:
    now = datetime.now(UTC)
    source_health = DashboardSourceHealthOut(total_sources=0, healthy_sources=0, failed_sources=0)
    return DashboardBriefingOut(
        generated_at=now,
        briefing_available=False,
        briefing_unavailable_reason=(
            "AI briefing is unavailable because there are no completed runs yet."
        ),
        briefing_items=[],
        recent_topics=[],
        latest_run=DashboardLatestRunOut(
            id=0,
            status="no_data",
            created_at=now,
            candidate_count=0,
        ),
        pipeline_metrics=DashboardPipelineMetricsOut(stages=[], drop_reasons={}),
        source_health=source_health,
    )


def _default_unavailable_reason(*, recent_topics: list[DashboardRecentTopicOut]) -> str | None:
    mode = settings.briefing_summarizer_mode.strip().lower()
    if mode != "llm":
        return "AI briefing is disabled by configuration."
    if not settings.openai_api_key.strip():
        return "AI briefing is unavailable because OPENAI_API_KEY is missing."
    if not recent_topics:
        return "AI briefing is unavailable because there are no recent topics to evaluate."
    return None


def _get_cached_briefing(*, run_id: int) -> _BriefingCacheEntry | None:
    with _BRIEFING_CACHE_LOCK:
        return _BRIEFING_CACHE_BY_RUN.get(run_id)


def _set_cached_briefing(
    *,
    run_id: int,
    briefing_available: bool,
    briefing_unavailable_reason: str | None,
    briefing_items: list[DashboardBriefingItemOut],
) -> None:
    with _BRIEFING_CACHE_LOCK:
        _BRIEFING_CACHE_BY_RUN[run_id] = _BriefingCacheEntry(
            run_id=run_id,
            generated_at=datetime.now(UTC),
            briefing_available=briefing_available,
            briefing_unavailable_reason=briefing_unavailable_reason,
            briefing_items=list(briefing_items),
        )


def clear_briefing_cache_for_tests() -> None:
    with _BRIEFING_CACHE_LOCK:
        _BRIEFING_CACHE_BY_RUN.clear()


def _load_labels_map(*, db_session: Session, topic_cluster_ids: list[int]) -> dict[int, list[str]]:
    if not topic_cluster_ids:
        return {}

    rows = db_session.execute(
        select(TopicLabelLink.topic_cluster_id, Label.name)
        .join(Label, Label.id == TopicLabelLink.label_id)
        .where(TopicLabelLink.topic_cluster_id.in_(topic_cluster_ids))
    ).all()

    labels_map: dict[int, list[str]] = defaultdict(list)
    for topic_cluster_id, label_name in rows:
        labels_map[int(topic_cluster_id)].append(str(label_name))

    return {
        topic_cluster_id: sorted(set(labels))
        for topic_cluster_id, labels in labels_map.items()
    }


def _classify_movement(*, current_score: float, previous_scores: list[float]) -> str:
    if not previous_scores:
        return "new"
    previous_avg = sum(previous_scores) / len(previous_scores)
    delta = current_score - previous_avg
    if delta >= 5.0:
        return "rising"
    if delta <= -5.0:
        return "cooling"
    return "stable"


def _to_recent_topic(
    *,
    candidate: ContentCandidate,
    cluster: TopicCluster,
    labels: list[str],
    movement: str,
) -> DashboardRecentTopicOut:
    return DashboardRecentTopicOut(
        candidate_id=candidate.id,
        run_id=candidate.run_id,
        canonical_topic=cluster.canonical_topic,
        trend_score=round(float(candidate.trend_score), 2),
        movement=movement,
        why_now=candidate.why_now,
        source_count=cluster.source_count,
        signal_count=cluster.signal_count,
        labels=labels,
        created_at=candidate.created_at,
    )


def _build_source_health(*, source_rows: list[RunSource]) -> DashboardSourceHealthOut:
    total_sources = len(source_rows)
    failed_sources = sum(
        1 for row in source_rows if row.status.strip().lower() in {"failed", "error", "timeout"}
    )
    healthy_sources = max(total_sources - failed_sources, 0)
    return DashboardSourceHealthOut(
        total_sources=total_sources,
        healthy_sources=healthy_sources,
        failed_sources=failed_sources,
    )


def _build_pipeline_metrics(
    *,
    source_rows: list[RunSource],
    latest_run_id: int,
    db_session: Session,
) -> DashboardPipelineMetricsOut:
    collected_count = sum(max(row.fetched_count, 0) for row in source_rows)
    normalized_count = collected_count

    relevance_signals = (
        db_session.scalar(
            select(func.coalesce(func.sum(TopicCluster.signal_count), 0)).where(
                TopicCluster.run_id == latest_run_id
            )
        )
        or 0
    )
    cluster_count = (
        db_session.scalar(
            select(func.count(TopicCluster.id)).where(TopicCluster.run_id == latest_run_id)
        )
        or 0
    )
    candidate_count = (
        db_session.scalar(
            select(func.count(ContentCandidate.id)).where(ContentCandidate.run_id == latest_run_id)
        )
        or 0
    )

    deduplicated_count = max(int(relevance_signals), int(cluster_count), int(candidate_count))
    deduplicated_count = min(deduplicated_count, int(normalized_count))
    relevance_passed_count = min(int(relevance_signals), deduplicated_count)
    clustered_count = min(int(cluster_count), relevance_passed_count)
    shortlisted_count = min(int(candidate_count), clustered_count)

    stages = [
        _stage(
            stage_key="collected",
            label="Collected",
            input_count=collected_count,
            kept_count=collected_count,
        ),
        _stage(
            stage_key="normalized",
            label="Normalized",
            input_count=collected_count,
            kept_count=normalized_count,
        ),
        _stage(
            stage_key="deduplicated",
            label="Deduplicated",
            input_count=normalized_count,
            kept_count=deduplicated_count,
        ),
        _stage(
            stage_key="relevance_passed",
            label="Relevance Passed",
            input_count=deduplicated_count,
            kept_count=relevance_passed_count,
        ),
        _stage(
            stage_key="clustered",
            label="Clustered",
            input_count=relevance_passed_count,
            kept_count=clustered_count,
        ),
        _stage(
            stage_key="shortlisted",
            label="Shortlisted",
            input_count=clustered_count,
            kept_count=shortlisted_count,
        ),
    ]

    drop_reasons = {
        "source_failures": sum(
            1 for row in source_rows if row.status.strip().lower() in {"failed", "error", "timeout"}
        ),
        "deduplicated_or_filtered": max(collected_count - relevance_passed_count, 0),
        "cluster_compaction": max(relevance_passed_count - clustered_count, 0),
        "shortlist_cutoff": max(clustered_count - shortlisted_count, 0),
    }

    return DashboardPipelineMetricsOut(stages=stages, drop_reasons=drop_reasons)


def _stage(
    *,
    stage_key: str,
    label: str,
    input_count: int,
    kept_count: int,
) -> DashboardPipelineStageOut:
    safe_input = max(int(input_count), 0)
    safe_kept = min(max(int(kept_count), 0), safe_input)
    dropped_count = safe_input - safe_kept
    drop_rate = round((dropped_count / safe_input) * 100.0, 2) if safe_input else 0.0
    return DashboardPipelineStageOut(
        stage_key=stage_key,
        label=label,
        input_count=safe_input,
        kept_count=safe_kept,
        dropped_count=dropped_count,
        drop_rate=drop_rate,
    )
