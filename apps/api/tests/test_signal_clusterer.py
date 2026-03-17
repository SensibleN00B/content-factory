from __future__ import annotations

from datetime import UTC, datetime

from app.domain.processing.clusterer import SignalClusterer
from app.domain.processing.normalizer import NormalizedSignal


def make_normalized_signal(
    *,
    source: str,
    source_signal_id: str,
    topic_candidate: str,
    title: str | None = None,
    url: str | None = None,
) -> NormalizedSignal:
    return NormalizedSignal(
        source=source,
        source_signal_id=source_signal_id,
        query=None,
        title=title or topic_candidate,
        topic_candidate=topic_candidate,
        url=url,
        published_at=datetime(2026, 3, 17, 10, 0, 0, tzinfo=UTC),
        raw_text=topic_candidate,
        engagement={"votes": 0, "comments": 0, "views": 0, "search_traffic": 0, "total": 0},
        author=None,
        tags=[],
        language="en",
        metadata={},
        raw_payload={},
    )


def test_clusterer_groups_similar_topics_into_one_cluster() -> None:
    clusterer = SignalClusterer()
    signals = [
        make_normalized_signal(
            source="reddit",
            source_signal_id="1",
            topic_candidate="AI receptionist for clinics",
            url="https://example.com/1",
        ),
        make_normalized_signal(
            source="youtube",
            source_signal_id="2",
            topic_candidate="AI voice receptionist",
            url="https://example.com/2",
        ),
        make_normalized_signal(
            source="hackernews",
            source_signal_id="3",
            topic_candidate="AI phone assistant for clinics",
            url="https://example.com/3",
        ),
    ]

    clusters = clusterer.cluster(signals)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.canonical_topic == "AI receptionist for clinics"
    assert cluster.signal_count == 3
    assert cluster.source_count == 3
    assert len(cluster.cluster_key) == 12
    assert cluster.evidence_urls == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]


def test_clusterer_keeps_unrelated_topics_in_separate_clusters() -> None:
    clusterer = SignalClusterer()
    signals = [
        make_normalized_signal(
            source="reddit",
            source_signal_id="1",
            topic_candidate="AI cold outreach automation",
        ),
        make_normalized_signal(
            source="youtube",
            source_signal_id="2",
            topic_candidate="Healthcare billing software pricing",
        ),
    ]

    clusters = clusterer.cluster(signals)

    assert len(clusters) == 2
    assert [cluster.canonical_topic for cluster in clusters] == [
        "AI cold outreach automation",
        "Healthcare billing software pricing",
    ]


def test_clusterer_produces_deterministic_cluster_key_independent_of_input_order() -> None:
    clusterer = SignalClusterer()
    first = make_normalized_signal(
        source="reddit",
        source_signal_id="1",
        topic_candidate="AI workflow automation for clinics",
    )
    second = make_normalized_signal(
        source="hackernews",
        source_signal_id="2",
        topic_candidate="Clinic AI workflow automation",
    )

    key_forward = clusterer.cluster([first, second])[0].cluster_key
    key_reversed = clusterer.cluster([second, first])[0].cluster_key

    assert key_forward == key_reversed
