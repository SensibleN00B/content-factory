from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.domain.ingestion.connectors import SourceCollectedSignal
from app.domain.processing.normalizer import SignalNormalizer


def make_signal(
    *,
    source: str = "reddit",
    title: str | None = "  AI&nbsp; receptionist \n",
    url: str | None = " https://example.com/post ",
    published_at: datetime | None = None,
    metadata: dict | None = None,
    engagement: dict | None = None,
    raw_payload: dict | None = None,
) -> SourceCollectedSignal:
    return SourceCollectedSignal(
        source=source,
        source_signal_id="sig-1",
        title=title,
        url=url,
        published_at=published_at,
        raw_payload=raw_payload or {},
        metadata=metadata or {},
        engagement=engagement or {},
    )


def test_signal_normalizer_maps_signal_to_unified_shape() -> None:
    normalizer = SignalNormalizer()
    signal = make_signal(
        metadata={
            "query": "ai receptionist",
            "author": " founder_123 ",
            "tags": [" AI ", "clinic", "", "clinic"],
            "language": " en ",
        },
        engagement={"upvotes": "10", "comments": 3, "likes": "2"},
        raw_payload={"selftext": "  We need &amp; want an <b>AI</b> assistant  "},
        published_at=datetime(2026, 3, 17, 12, 0, 0),
    )

    normalized = normalizer.normalize(signal)

    assert normalized.source == "reddit"
    assert normalized.query == "ai receptionist"
    assert normalized.title == "AI receptionist"
    assert normalized.url == "https://example.com/post"
    assert normalized.published_at == datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC)
    assert normalized.raw_text == "We need & want an AI assistant"
    assert normalized.topic_candidate == "AI receptionist"
    assert normalized.author == "founder_123"
    assert normalized.tags == ["ai", "clinic"]
    assert normalized.language == "en"
    assert normalized.engagement == {
        "votes": 12,
        "comments": 3,
        "views": 0,
        "search_traffic": 0,
        "total": 15,
    }


def test_signal_normalizer_converts_datetime_to_utc_and_uses_query_fallback() -> None:
    normalizer = SignalNormalizer()
    plus_three = timezone(timedelta(hours=3))
    signal = make_signal(
        source="google_trends",
        title=None,
        metadata={"query_match": "voice ai", "region": "US"},
        raw_payload={"snippet": "  voice   AI for clinics   "},
        engagement={"search_traffic": "1,200+"},
        published_at=datetime(2026, 3, 17, 9, 30, 0, tzinfo=plus_three),
    )

    normalized = normalizer.normalize(signal)

    assert normalized.query == "voice ai"
    assert normalized.title is None
    assert normalized.topic_candidate == "voice AI for clinics"
    assert normalized.raw_text == "voice AI for clinics"
    assert normalized.published_at == datetime(2026, 3, 17, 6, 30, 0, tzinfo=UTC)
    assert normalized.engagement["search_traffic"] == 1200
    assert normalized.engagement["total"] == 1200


def test_signal_normalizer_normalize_many_keeps_order() -> None:
    normalizer = SignalNormalizer()
    first = make_signal(source="reddit", title=" First ")
    second = make_signal(source="youtube", title=" Second ", engagement={"views": "3K"})

    normalized = normalizer.normalize_many([first, second])

    assert [item.source for item in normalized] == ["reddit", "youtube"]
    assert [item.title for item in normalized] == ["First", "Second"]
    assert normalized[0].engagement["total"] == 0
    assert normalized[1].engagement["views"] == 3000
