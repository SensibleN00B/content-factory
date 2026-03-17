from __future__ import annotations

from datetime import UTC, datetime

from app.domain.processing.clusterer import TopicClusterDraft
from app.domain.processing.explainer import ExplainabilityConfig, TopicExplainer
from app.domain.processing.normalizer import NormalizedSignal
from app.domain.processing.scorer import ScoredTopicCandidate


def make_signal(*, source: str, source_signal_id: str, raw_text: str, url: str) -> NormalizedSignal:
    return NormalizedSignal(
        source=source,
        source_signal_id=source_signal_id,
        query=None,
        title=raw_text,
        topic_candidate=raw_text,
        url=url,
        published_at=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
        raw_text=raw_text,
        engagement={"votes": 0, "comments": 0, "views": 0, "search_traffic": 0, "total": 100},
        author=None,
        tags=[],
        language="en",
        metadata={},
        raw_payload={},
    )


def make_cluster(cluster_key: str) -> TopicClusterDraft:
    signals = [
        make_signal(
            source="reddit",
            source_signal_id="1",
            raw_text="AI workflow for clinics",
            url="https://example.com/1",
        ),
        make_signal(
            source="youtube",
            source_signal_id="2",
            raw_text="Why clinic AI workflow fails",
            url="https://example.com/2",
        ),
        make_signal(
            source="hackernews",
            source_signal_id="3",
            raw_text="CEO lessons from AI workflow rollout",
            url="https://example.com/3",
        ),
        make_signal(
            source="producthunt",
            source_signal_id="4",
            raw_text="New clinic AI workflow tools",
            url="https://example.com/4",
        ),
    ]
    return TopicClusterDraft(
        cluster_key=cluster_key,
        canonical_topic="AI workflow for clinics",
        signals=signals,
        source_count=4,
        signal_count=4,
        evidence_urls=[signal.url for signal in signals if signal.url is not None],
    )


def make_candidate(cluster_key: str) -> ScoredTopicCandidate:
    return ScoredTopicCandidate(
        cluster_key=cluster_key,
        canonical_topic="AI workflow for clinics",
        trend_score=82.3,
        score_breakdown={
            "velocity": 90.0,
            "volume": 78.0,
            "engagement": 74.0,
            "relevance": 96.0,
            "opinionability": 44.0,
        },
        source_count=4,
        signal_count=4,
        evidence_urls=[],
    )


def test_topic_explainer_builds_why_now_evidence_and_angles() -> None:
    explainer = TopicExplainer()
    candidate = make_candidate("cluster-a")
    clusters = {"cluster-a": make_cluster("cluster-a")}

    explained = explainer.explain([candidate], clusters_by_key=clusters)

    assert len(explained) == 1
    first = explained[0]
    assert first.why_now != ""
    assert "velocity" in first.why_now.lower() or "relevance" in first.why_now.lower()
    assert first.evidence_links == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]
    assert len(first.angles) == 3
    assert "AI workflow for clinics" in first.angles[0]


def test_topic_explainer_handles_missing_cluster_context() -> None:
    explainer = TopicExplainer()
    candidate = make_candidate("cluster-missing")
    config = ExplainabilityConfig(max_evidence_links=2, max_angles=2)

    explained = explainer.explain([candidate], clusters_by_key={}, config=config)

    assert len(explained) == 1
    first = explained[0]
    assert first.evidence_links == []
    assert len(first.angles) == 2
