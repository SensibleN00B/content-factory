from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.processing.clusterer import TopicClusterDraft
from app.domain.processing.normalizer import NormalizedSignal
from app.domain.processing.scorer import ScoringConfig, ScoringWeights, TopicScorer


def make_signal(
    *,
    source: str,
    source_signal_id: str,
    raw_text: str,
    engagement_total: int,
    published_at: datetime | None,
) -> NormalizedSignal:
    return NormalizedSignal(
        source=source,
        source_signal_id=source_signal_id,
        query=None,
        title=raw_text,
        topic_candidate=raw_text,
        url=f"https://example.com/{source_signal_id}",
        published_at=published_at,
        raw_text=raw_text,
        engagement={
            "votes": 0,
            "comments": 0,
            "views": 0,
            "search_traffic": 0,
            "total": engagement_total,
        },
        author=None,
        tags=[],
        language="en",
        metadata={},
        raw_payload={},
    )


def make_cluster(
    *,
    cluster_key: str,
    canonical_topic: str,
    signals: list[NormalizedSignal],
) -> TopicClusterDraft:
    evidence_urls = [signal.url for signal in signals if signal.url is not None]
    return TopicClusterDraft(
        cluster_key=cluster_key,
        canonical_topic=canonical_topic,
        signals=signals,
        source_count=len({signal.source for signal in signals}),
        signal_count=len(signals),
        evidence_urls=evidence_urls,
    )


def test_topic_scorer_ranks_clusters_and_returns_breakdown() -> None:
    now = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
    strong_cluster = make_cluster(
        cluster_key="cluster-a",
        canonical_topic="AI workflow for clinics",
        signals=[
            make_signal(
                source="reddit",
                source_signal_id="a1",
                raw_text="AI workflow for clinics",
                engagement_total=220,
                published_at=now - timedelta(hours=2),
            ),
            make_signal(
                source="youtube",
                source_signal_id="a2",
                raw_text="CEO guide to clinic AI workflow",
                engagement_total=180,
                published_at=now - timedelta(hours=5),
            ),
            make_signal(
                source="hackernews",
                source_signal_id="a3",
                raw_text="Why clinic AI workflow fails",
                engagement_total=140,
                published_at=now - timedelta(hours=8),
            ),
        ],
    )
    weak_cluster = make_cluster(
        cluster_key="cluster-b",
        canonical_topic="General tech updates",
        signals=[
            make_signal(
                source="reddit",
                source_signal_id="b1",
                raw_text="General tech updates",
                engagement_total=20,
                published_at=now - timedelta(hours=96),
            ),
            make_signal(
                source="youtube",
                source_signal_id="b2",
                raw_text="Weekly tech roundup",
                engagement_total=12,
                published_at=now - timedelta(hours=120),
            ),
        ],
    )

    scorer = TopicScorer()
    config = ScoringConfig(
        relevance_terms=["ai", "clinic", "ceo"],
        reference_time=now,
    )

    results = scorer.score_clusters([weak_cluster, strong_cluster], config=config)

    assert [item.cluster_key for item in results] == ["cluster-a", "cluster-b"]
    assert set(results[0].score_breakdown.keys()) == {
        "velocity",
        "volume",
        "engagement",
        "relevance",
        "opinionability",
    }
    assert 0 <= results[0].trend_score <= 100
    assert 0 <= results[1].trend_score <= 100


def test_topic_scorer_respects_custom_weights() -> None:
    now = datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
    relevance_heavy = make_cluster(
        cluster_key="cluster-a",
        canonical_topic="AI clinic automation for business owner",
        signals=[
            make_signal(
                source="reddit",
                source_signal_id="a1",
                raw_text="AI clinic automation for business owner",
                engagement_total=10,
                published_at=now - timedelta(hours=6),
            ),
        ],
    )
    engagement_heavy = make_cluster(
        cluster_key="cluster-b",
        canonical_topic="Entertainment roundup",
        signals=[
            make_signal(
                source="youtube",
                source_signal_id="b1",
                raw_text="Entertainment roundup",
                engagement_total=500,
                published_at=now - timedelta(hours=6),
            ),
        ],
    )

    scorer = TopicScorer()
    config = ScoringConfig(
        relevance_terms=["ai", "clinic", "business owner"],
        reference_time=now,
        weights=ScoringWeights(
            velocity=0.1,
            volume=0.1,
            engagement=0.1,
            relevance=0.6,
            opinionability=0.1,
        ),
    )

    results = scorer.score_clusters([engagement_heavy, relevance_heavy], config=config)

    assert results[0].cluster_key == "cluster-a"


def test_topic_scorer_handles_missing_dates_without_crashing() -> None:
    cluster = make_cluster(
        cluster_key="cluster-a",
        canonical_topic="AI automation",
        signals=[
            make_signal(
                source="reddit",
                source_signal_id="a1",
                raw_text="AI automation",
                engagement_total=50,
                published_at=None,
            ),
        ],
    )
    scorer = TopicScorer()
    config = ScoringConfig(relevance_terms=["ai"])

    results = scorer.score_clusters([cluster], config=config)

    assert len(results) == 1
    assert results[0].score_breakdown["velocity"] >= 0
