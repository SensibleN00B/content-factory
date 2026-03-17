from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.domain.ingestion.connectors import SourceCollectedSignal, SourceCollectRequest
from app.domain.ingestion.registry import SourceRegistry
from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy
from app.domain.processing.explainer import ExplainabilityConfig, TopicExplainer
from app.domain.processing.normalizer import SignalNormalizer
from app.domain.processing.relevance_filter import RelevanceFilterConfig, SignalRelevanceFilter
from app.domain.processing.scorer import ScoringConfig, TopicScorer
from app.services.trend_pipeline import TrendPipeline


def make_request() -> SourceCollectRequest:
    return SourceCollectRequest(
        keywords=["ai workflow", "clinic automation"],
        regions=["US", "CA"],
        language="en",
        limit=10,
    )


def make_signal(
    *,
    source: str,
    signal_id: str,
    title: str,
    url: str,
    hours_ago: int,
    engagement_total: int,
) -> SourceCollectedSignal:
    now = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
    return SourceCollectedSignal(
        source=source,
        source_signal_id=signal_id,
        title=title,
        url=url,
        published_at=now - timedelta(hours=hours_ago),
        raw_payload={"text": title},
        metadata={
            "query": "ai workflow",
            "author": "founder",
            "tags": ["ai", "clinic", "founder"],
            "language": "en",
            "region": "US",
        },
        engagement={"upvotes": engagement_total, "comments": 4},
    )


def test_trend_pipeline_produces_explained_candidates_from_fixture_sources() -> None:
    class RedditConnector:
        source_key = "reddit"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [
                make_signal(
                    source="reddit",
                    signal_id="r1",
                    title="AI workflow for clinics",
                    url="https://example.com/r1",
                    hours_ago=2,
                    engagement_total=80,
                ),
                make_signal(
                    source="reddit",
                    signal_id="r2",
                    title="Clinic automation with AI agents",
                    url="https://example.com/r2",
                    hours_ago=4,
                    engagement_total=60,
                ),
            ]

    class HNConnector:
        source_key = "hackernews"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [
                make_signal(
                    source="hackernews",
                    signal_id="h1",
                    title="Why AI clinic workflows fail without integration",
                    url="https://example.com/h1",
                    hours_ago=7,
                    engagement_total=50,
                ),
            ]

    registry = SourceRegistry(connectors=[RedditConnector(), HNConnector()])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.2, max_retries=1),
    )
    pipeline = TrendPipeline(
        runner=runner,
        normalizer=SignalNormalizer(),
        relevance_filter=SignalRelevanceFilter(),
        scorer=TopicScorer(),
        explainer=TopicExplainer(),
    )

    result = pipeline.run(
        request=make_request(),
        relevance_config=RelevanceFilterConfig(
            niche_terms=["ai", "automation"],
            icp_terms=["founder", "ceo", "cto"],
            allowed_regions=["US", "CA"],
            language="en",
            include_keywords=["clinic"],
            exclude_keywords=["crypto"],
        ),
        scoring_config=ScoringConfig(
            relevance_terms=["ai", "clinic", "workflow"],
            reference_time=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
        ),
        explainability_config=ExplainabilityConfig(max_evidence_links=3, max_angles=3),
    )

    assert len(result.explained_candidates) >= 1
    assert result.explained_candidates[0].trend_score > 0
    assert len(result.explained_candidates[0].evidence_links) >= 1
    assert len(result.explained_candidates[0].angles) >= 2


def test_trend_pipeline_keeps_working_when_one_source_fails() -> None:
    class BrokenConnector:
        source_key = "broken"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            raise RuntimeError("boom")

    class HealthyConnector:
        source_key = "reddit"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [
                make_signal(
                    source="reddit",
                    signal_id="r1",
                    title="AI workflow for clinics",
                    url="https://example.com/r1",
                    hours_ago=1,
                    engagement_total=100,
                ),
            ]

    registry = SourceRegistry(connectors=[BrokenConnector(), HealthyConnector()])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.2, max_retries=0),
    )
    pipeline = TrendPipeline(
        runner=runner,
        normalizer=SignalNormalizer(),
        relevance_filter=SignalRelevanceFilter(),
        scorer=TopicScorer(),
        explainer=TopicExplainer(),
    )

    result = pipeline.run(
        request=make_request(),
        sources=["broken", "reddit"],
        relevance_config=RelevanceFilterConfig(
            niche_terms=["ai"],
            icp_terms=["founder"],
            allowed_regions=["US"],
            language="en",
            include_keywords=["clinic"],
            exclude_keywords=[],
        ),
        scoring_config=ScoringConfig(relevance_terms=["ai", "clinic"]),
        explainability_config=ExplainabilityConfig(),
    )

    assert result.run_summary.results["broken"].status == "failed"
    assert result.run_summary.results["reddit"].status == "success"
    assert len(result.explained_candidates) == 1


def test_trend_pipeline_emits_completion_metrics(caplog: object) -> None:
    caplog.set_level(logging.INFO)

    class BrokenConnector:
        source_key = "broken"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            raise RuntimeError("boom")

    class HealthyConnector:
        source_key = "reddit"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [
                make_signal(
                    source="reddit",
                    signal_id="r1",
                    title="AI workflow for clinics",
                    url="https://example.com/r1",
                    hours_ago=1,
                    engagement_total=100,
                ),
            ]

    registry = SourceRegistry(connectors=[BrokenConnector(), HealthyConnector()])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.2, max_retries=0),
    )
    pipeline = TrendPipeline(
        runner=runner,
        normalizer=SignalNormalizer(),
        relevance_filter=SignalRelevanceFilter(),
        scorer=TopicScorer(),
        explainer=TopicExplainer(),
    )

    result = pipeline.run(
        request=make_request(),
        sources=["broken", "reddit"],
        relevance_config=RelevanceFilterConfig(
            niche_terms=["ai"],
            icp_terms=["founder"],
            allowed_regions=["US"],
            language="en",
            include_keywords=["clinic"],
            exclude_keywords=[],
        ),
        scoring_config=ScoringConfig(relevance_terms=["ai", "clinic"]),
        explainability_config=ExplainabilityConfig(),
    )

    assert result.metrics.duration_ms >= 0
    assert result.metrics.source_failures == 1
    assert result.metrics.candidate_count == len(result.explained_candidates)

    completion_record = None
    for record in caplog.records:
        if getattr(record, "event", None) == "trend_pipeline.completed":
            completion_record = record
            break

    assert completion_record is not None
    assert getattr(completion_record, "source_failures", None) == 1
    assert getattr(completion_record, "candidate_count", None) == len(result.explained_candidates)
    assert getattr(completion_record, "duration_ms", None) is not None
