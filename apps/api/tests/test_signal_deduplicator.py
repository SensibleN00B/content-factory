from __future__ import annotations

from datetime import UTC, datetime

from app.domain.processing.deduplicator import SignalDeduplicator
from app.domain.processing.normalizer import NormalizedSignal


def make_normalized_signal(
    *,
    source: str = "reddit",
    source_signal_id: str | None = None,
    title: str | None = None,
    topic_candidate: str | None = None,
    url: str | None = None,
) -> NormalizedSignal:
    return NormalizedSignal(
        source=source,
        source_signal_id=source_signal_id,
        query=None,
        title=title,
        topic_candidate=topic_candidate,
        url=url,
        published_at=datetime(2026, 3, 17, 10, 0, 0, tzinfo=UTC),
        raw_text=title or topic_candidate or "",
        engagement={"votes": 0, "comments": 0, "views": 0, "search_traffic": 0, "total": 0},
        author=None,
        tags=[],
        language="en",
        metadata={},
        raw_payload={},
    )


def test_deduplicator_drops_duplicate_by_url_hash() -> None:
    deduplicator = SignalDeduplicator()
    first = make_normalized_signal(
        source_signal_id="1",
        title="AI receptionist",
        topic_candidate="AI receptionist",
        url="https://Example.com/topic/1",
    )
    duplicate = make_normalized_signal(
        source_signal_id="2",
        title="Another title",
        topic_candidate="Another title",
        url=" https://example.com/topic/1/ ",
    )

    result = deduplicator.deduplicate([first, duplicate])

    assert [item.source_signal_id for item in result.unique_signals] == ["1"]
    assert result.dropped_by_rule["url"] == 1
    assert result.dropped_by_rule["title"] == 0
    assert result.dropped_by_rule["topic"] == 0


def test_deduplicator_drops_duplicate_by_title_hash_when_urls_differ() -> None:
    deduplicator = SignalDeduplicator()
    first = make_normalized_signal(
        source_signal_id="1",
        title=" Voice AI for clinics ",
        topic_candidate="Voice AI for clinics",
        url="https://example.com/1",
    )
    duplicate = make_normalized_signal(
        source_signal_id="2",
        title="voice ai for CLINICS",
        topic_candidate="Different topic",
        url="https://example.com/2",
    )

    result = deduplicator.deduplicate([first, duplicate])

    assert [item.source_signal_id for item in result.unique_signals] == ["1"]
    assert result.dropped_by_rule["url"] == 0
    assert result.dropped_by_rule["title"] == 1
    assert result.dropped_by_rule["topic"] == 0


def test_deduplicator_drops_duplicate_by_topic_hash_when_title_missing() -> None:
    deduplicator = SignalDeduplicator()
    first = make_normalized_signal(
        source_signal_id="1",
        title=None,
        topic_candidate="AI automation for cold outreach",
        url="https://example.com/1",
    )
    duplicate = make_normalized_signal(
        source_signal_id="2",
        title=None,
        topic_candidate=" ai automation for cold outreach ",
        url="https://example.com/2",
    )

    result = deduplicator.deduplicate([first, duplicate])

    assert [item.source_signal_id for item in result.unique_signals] == ["1"]
    assert result.dropped_by_rule["url"] == 0
    assert result.dropped_by_rule["title"] == 0
    assert result.dropped_by_rule["topic"] == 1


def test_deduplicator_keeps_non_duplicates_in_input_order() -> None:
    deduplicator = SignalDeduplicator()
    first = make_normalized_signal(
        source_signal_id="1",
        title="AI receptionist",
        topic_candidate="AI receptionist",
        url="https://example.com/1",
    )
    second = make_normalized_signal(
        source_signal_id="2",
        title="AI outbound calls",
        topic_candidate="AI outbound calls",
        url="https://example.com/2",
    )
    third_duplicate = make_normalized_signal(
        source_signal_id="3",
        title="ai outbound calls",
        topic_candidate="AI outbound calls",
        url="https://example.com/3",
    )

    result = deduplicator.deduplicate([first, second, third_duplicate])

    assert [item.source_signal_id for item in result.unique_signals] == ["1", "2"]
    assert [item.source_signal_id for item in result.dropped_signals] == ["3"]
