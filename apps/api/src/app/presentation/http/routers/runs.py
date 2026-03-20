from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.observability import log_event
from app.core.config import settings
from app.domain.ingestion.connectors import SourceCollectRequest
from app.domain.ingestion.registry import SourceRegistry
from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy
from app.domain.processing.explainer import ExplainabilityConfig, TopicExplainer
from app.domain.processing.normalizer import SignalNormalizer
from app.domain.processing.relevance_filter import RelevanceFilterConfig, SignalRelevanceFilter
from app.domain.processing.scorer import ScoringConfig, TopicScorer
from app.domain.runs.state_machine import RunStateMachine
from app.infrastructure.db.models import ContentCandidate, Profile, Run, RunSource, TopicCluster
from app.infrastructure.db.session import get_db_session
from app.infrastructure.sources import (
    GoogleTrendsApiClient,
    GoogleTrendsSourceConnector,
    HackerNewsApiClient,
    HackerNewsSourceConnector,
    ProductHuntApiClient,
    ProductHuntCredentials,
    ProductHuntSourceConnector,
    RedditApiClient,
    RedditCredentials,
    RedditSourceConnector,
    YouTubeApiClient,
    YouTubeCredentials,
    YouTubeSourceConnector,
)
from app.presentation.http.schemas.run import RunOut, RunSourceOut
from app.services.trend_pipeline import TrendPipeline

DbSession = Annotated[Session, Depends(get_db_session)]
RunExecutor = Callable[[int, sessionmaker[Session]], None]

router = APIRouter(prefix="/api", tags=["runs"])
MVP_SOURCE_KEYS = ["google_trends", "reddit", "hackernews", "producthunt", "youtube"]
logger = logging.getLogger(__name__)


def _profile_snapshot(profile: Profile) -> dict[str, Any]:
    return {
        "niche": profile.niche or [],
        "icp": profile.icp or [],
        "regions": profile.regions or [],
        "language": profile.language,
        "seeds": profile.seeds or [],
        "negatives": profile.negatives or [],
        "settings": profile.settings_json or {},
    }


def _to_run_out(run: Run, *, sources: list[RunSource]) -> RunOut:
    return RunOut(
        id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_snapshot=run.input_snapshot_json,
        error_summary=run.error_summary,
        created_at=run.created_at,
        sources=[
            RunSourceOut(
                source=source.source,
                status=source.status,
                fetched_count=source.fetched_count,
                error_text=source.error_text,
                duration_ms=source.duration_ms,
                created_at=source.created_at,
            )
            for source in sources
        ],
    )


def _fetch_run_sources(db_session: Session, *, run_id: int) -> list[RunSource]:
    return list(
        db_session.scalars(
            select(RunSource).where(RunSource.run_id == run_id).order_by(RunSource.source.asc())
        )
    )


def _build_background_session_factory(db_session: Session) -> sessionmaker[Session]:
    return sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_values = value
    elif isinstance(value, str):
        raw_values = [value]
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def _build_collect_request(snapshot: dict[str, Any]) -> SourceCollectRequest:
    seeds = _normalize_string_list(snapshot.get("seeds"))
    niche = _normalize_string_list(snapshot.get("niche"))
    icp = _normalize_string_list(snapshot.get("icp"))
    regions = _normalize_string_list(snapshot.get("regions")) or ["US"]
    language = str(snapshot.get("language") or "en").strip().lower() or "en"
    keywords = seeds or niche or icp or ["ai"]

    return SourceCollectRequest(
        keywords=keywords,
        regions=[region.upper() for region in regions],
        language=language,
        limit=25,
    )


def _build_relevance_config(snapshot: dict[str, Any]) -> RelevanceFilterConfig:
    return RelevanceFilterConfig(
        niche_terms=_normalize_string_list(snapshot.get("niche")),
        icp_terms=_normalize_string_list(snapshot.get("icp")),
        allowed_regions=_normalize_string_list(snapshot.get("regions")),
        language=str(snapshot.get("language") or "en").strip().lower() or "en",
        include_keywords=_normalize_string_list(snapshot.get("seeds")),
        exclude_keywords=_normalize_string_list(snapshot.get("negatives")),
    )


def _build_scoring_config(snapshot: dict[str, Any]) -> ScoringConfig:
    relevance_terms = [
        *_normalize_string_list(snapshot.get("niche")),
        *_normalize_string_list(snapshot.get("icp")),
        *_normalize_string_list(snapshot.get("seeds")),
    ]
    return ScoringConfig(relevance_terms=relevance_terms)


def _build_source_registry() -> SourceRegistry:
    return SourceRegistry(
        connectors=[
            GoogleTrendsSourceConnector(api_client=GoogleTrendsApiClient()),
            RedditSourceConnector(
                api_client=RedditApiClient(
                    credentials=RedditCredentials(
                        client_id=settings.reddit_client_id,
                        client_secret=settings.reddit_client_secret,
                        user_agent=settings.reddit_user_agent,
                    )
                )
            ),
            HackerNewsSourceConnector(api_client=HackerNewsApiClient()),
            ProductHuntSourceConnector(
                api_client=ProductHuntApiClient(
                    credentials=ProductHuntCredentials(
                        client_id=settings.producthunt_client_id,
                        client_secret=settings.producthunt_client_secret,
                    )
                )
            ),
            YouTubeSourceConnector(
                api_client=YouTubeApiClient(
                    credentials=YouTubeCredentials(api_key=settings.youtube_api_key)
                )
            ),
        ]
    )


def _build_pipeline() -> TrendPipeline:
    registry = _build_source_registry()
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=15.0, max_retries=0, retry_delay_seconds=0.0),
    )
    return TrendPipeline(
        runner=runner,
        normalizer=SignalNormalizer(),
        relevance_filter=SignalRelevanceFilter(),
        scorer=TopicScorer(),
        explainer=TopicExplainer(),
    )


def _apply_source_results(
    *,
    db_session: Session,
    run_id: int,
    source_results: dict[str, Any],
) -> None:
    run_sources = _fetch_run_sources(db_session, run_id=run_id)
    by_source = {source.source: source for source in run_sources}
    for source_key in MVP_SOURCE_KEYS:
        row = by_source.get(source_key)
        if row is None:
            continue

        result = source_results.get(source_key)
        if result is None:
            row.status = "failed"
            row.error_text = "Source result is missing"
            row.duration_ms = row.duration_ms or 0
            row.fetched_count = 0
            db_session.add(row)
            continue

        row.status = "success" if result.status == "success" else result.status
        row.error_text = result.error_message
        row.duration_ms = result.duration_ms
        row.fetched_count = len(result.signals)
        db_session.add(row)
    db_session.commit()


def _persist_candidates(
    *,
    db_session: Session,
    run_id: int,
    clusters: list[Any],
    explained_candidates: list[Any],
) -> None:
    db_session.execute(delete(ContentCandidate).where(ContentCandidate.run_id == run_id))
    db_session.execute(delete(TopicCluster).where(TopicCluster.run_id == run_id))
    db_session.commit()

    cluster_id_by_key: dict[str, int] = {}
    for cluster in clusters:
        topic_cluster = TopicCluster(
            run_id=run_id,
            canonical_topic=cluster.canonical_topic,
            cluster_hash=cluster.cluster_key,
            source_count=cluster.source_count,
            signal_count=cluster.signal_count,
            evidence_urls_json=list(cluster.evidence_urls),
        )
        db_session.add(topic_cluster)
        db_session.flush()
        cluster_id_by_key[cluster.cluster_key] = topic_cluster.id

    for candidate in explained_candidates:
        topic_cluster_id = cluster_id_by_key.get(candidate.cluster_key)
        if topic_cluster_id is None:
            continue
        db_session.add(
            ContentCandidate(
                run_id=run_id,
                topic_cluster_id=topic_cluster_id,
                trend_score=candidate.trend_score,
                score_breakdown_json=dict(candidate.score_breakdown),
                why_now=candidate.why_now,
                angles_json=list(candidate.angles),
                confidence=round(candidate.trend_score / 100.0, 2),
            )
        )

    db_session.commit()


def _execute_run(run_id: int, session_factory: sessionmaker[Session]) -> None:
    db_session = session_factory()
    state_machine = RunStateMachine()
    try:
        run = db_session.get(Run, run_id)
        if run is None:
            return

        if run.status != "pending":
            return

        run = state_machine.transition(
            db_session=db_session,
            run=run,
            target_status="collecting",
        )
        for source in _fetch_run_sources(db_session, run_id=run_id):
            source.status = "collecting"
            source.error_text = None
            source.duration_ms = None
            db_session.add(source)
        db_session.commit()

        snapshot = run.input_snapshot_json or {}
        pipeline = _build_pipeline()
        result = pipeline.run(
            request=_build_collect_request(snapshot),
            relevance_config=_build_relevance_config(snapshot),
            scoring_config=_build_scoring_config(snapshot),
            explainability_config=ExplainabilityConfig(),
            sources=MVP_SOURCE_KEYS,
        )

        _apply_source_results(
            db_session=db_session,
            run_id=run_id,
            source_results=result.run_summary.results,
        )
        run = state_machine.transition(
            db_session=db_session,
            run=run,
            target_status="processing",
        )
        _persist_candidates(
            db_session=db_session,
            run_id=run_id,
            clusters=result.clusters,
            explained_candidates=result.explained_candidates,
        )
        run = state_machine.transition(
            db_session=db_session,
            run=run,
            target_status="scoring",
        )
        state_machine.transition(
            db_session=db_session,
            run=run,
            target_status="completed",
        )
        log_event(
            logger,
            logging.INFO,
            "run.execution_completed",
            run_id=run_id,
            candidate_count=result.metrics.candidate_count,
            source_failures=result.metrics.source_failures,
        )
    except Exception as exc:  # noqa: BLE001
        db_session.rollback()
        run = db_session.get(Run, run_id)
        if run is not None and run.status in {"pending", "collecting", "processing", "scoring"}:
            state_machine.transition(
                db_session=db_session,
                run=run,
                target_status="failed",
                error_summary=str(exc),
            )
        for source in _fetch_run_sources(db_session, run_id=run_id):
            if source.status in {"pending", "collecting", "processing", "scoring"}:
                source.status = "failed"
                source.error_text = str(exc)
                db_session.add(source)
        db_session.commit()
        log_event(
            logger,
            logging.ERROR,
            "run.execution_failed",
            run_id=run_id,
            error_message=str(exc),
        )
    finally:
        db_session.close()


def get_run_executor() -> RunExecutor:
    return _execute_run


@router.post("/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(
    background_tasks: BackgroundTasks,
    db_session: DbSession,
    run_executor: Annotated[RunExecutor, Depends(get_run_executor)],
) -> RunOut:
    profile = db_session.scalar(select(Profile).order_by(Profile.id.asc()).limit(1))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile is not initialized",
        )

    run = Run(
        profile_id=profile.id,
        status="pending",
        input_snapshot_json=_profile_snapshot(profile),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    for source_key in MVP_SOURCE_KEYS:
        db_session.add(
            RunSource(
                run_id=run.id,
                source=source_key,
                status="pending",
                fetched_count=0,
                error_text=None,
                duration_ms=None,
            )
        )
    db_session.commit()
    run_sources = _fetch_run_sources(db_session, run_id=run.id)

    log_event(
        logger,
        logging.INFO,
        "run.created",
        run_id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        source_count=len(run_sources),
    )

    background_tasks.add_task(
        run_executor,
        run.id,
        _build_background_session_factory(db_session),
    )

    return _to_run_out(run, sources=run_sources)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db_session: DbSession) -> RunOut:
    run = db_session.get(Run, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    run_sources = _fetch_run_sources(db_session, run_id=run_id)
    candidate_count = (
        db_session.scalar(
            select(func.count(ContentCandidate.id)).where(ContentCandidate.run_id == run_id)
        )
        or 0
    )
    source_failures = sum(
        1 for source in run_sources if source.status.lower() in {"failed", "timeout"}
    )
    run_duration_ms: int | None = None
    if run.started_at is not None and run.finished_at is not None:
        run_duration_ms = max(0, int((run.finished_at - run.started_at).total_seconds() * 1000))

    log_event(
        logger,
        logging.INFO,
        "run.fetched",
        run_id=run.id,
        status=run.status,
        source_failures=source_failures,
        candidate_count=int(candidate_count),
        duration_ms=run_duration_ms,
    )

    return _to_run_out(run, sources=run_sources)
