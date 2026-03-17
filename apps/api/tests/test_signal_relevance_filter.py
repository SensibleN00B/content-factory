from __future__ import annotations

from datetime import UTC, datetime

from app.domain.processing.normalizer import NormalizedSignal
from app.domain.processing.relevance_filter import RelevanceFilterConfig, SignalRelevanceFilter


def make_normalized_signal(
    *,
    source_signal_id: str,
    title: str,
    topic_candidate: str,
    raw_text: str,
    language: str | None = "en",
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> NormalizedSignal:
    return NormalizedSignal(
        source="reddit",
        source_signal_id=source_signal_id,
        query=None,
        title=title,
        topic_candidate=topic_candidate,
        url=f"https://example.com/{source_signal_id}",
        published_at=datetime(2026, 3, 17, 12, 0, 0, tzinfo=UTC),
        raw_text=raw_text,
        engagement={"votes": 0, "comments": 0, "views": 0, "search_traffic": 0, "total": 0},
        author=None,
        tags=tags or [],
        language=language,
        metadata=metadata or {},
        raw_payload={},
    )


def make_config() -> RelevanceFilterConfig:
    return RelevanceFilterConfig(
        niche_terms=["ai", "automation"],
        icp_terms=["business owner", "ceo", "cto"],
        allowed_regions=["US", "CA", "EU"],
        language="en",
        include_keywords=["clinic", "workflow"],
        exclude_keywords=["crypto", "gaming"],
    )


def test_relevance_filter_keeps_relevant_signal() -> None:
    filter_engine = SignalRelevanceFilter()
    config = make_config()
    signal = make_normalized_signal(
        source_signal_id="1",
        title="AI workflow for clinic operations",
        topic_candidate="AI workflow for clinic operations",
        raw_text="Business owner guide for clinic AI automation",
        tags=["ceo", "ai"],
        metadata={"region": "US"},
    )

    result = filter_engine.filter([signal], config=config)

    assert [item.source_signal_id for item in result.kept_signals] == ["1"]
    assert result.excluded_signals == []


def test_relevance_filter_excludes_signal_with_negative_keyword() -> None:
    filter_engine = SignalRelevanceFilter()
    config = make_config()
    signal = make_normalized_signal(
        source_signal_id="2",
        title="AI gaming assistants",
        topic_candidate="AI gaming assistants",
        raw_text="How business owner communities discuss AI gaming tools",
        tags=["ceo", "gaming"],
        metadata={"region": "US"},
    )

    result = filter_engine.filter([signal], config=config)

    assert result.kept_signals == []
    assert len(result.excluded_signals) == 1
    assert result.excluded_signals[0].signal.source_signal_id == "2"
    assert "contains_excluded_keyword" in result.excluded_signals[0].reasons


def test_relevance_filter_excludes_signal_with_language_mismatch() -> None:
    filter_engine = SignalRelevanceFilter()
    config = make_config()
    signal = make_normalized_signal(
        source_signal_id="3",
        title="Automatisation IA pour clinique",
        topic_candidate="Automatisation IA pour clinique",
        raw_text="Guide CTO pour clinique",
        language="fr",
        tags=["cto"],
        metadata={"region": "EU"},
    )

    result = filter_engine.filter([signal], config=config)

    assert result.kept_signals == []
    assert "language_mismatch" in result.excluded_signals[0].reasons


def test_relevance_filter_excludes_signal_with_explicit_region_mismatch() -> None:
    filter_engine = SignalRelevanceFilter()
    config = make_config()
    signal = make_normalized_signal(
        source_signal_id="4",
        title="AI workflow for clinics",
        topic_candidate="AI workflow for clinics",
        raw_text="CTO handbook for clinic automation",
        tags=["cto"],
        metadata={"region": "BR"},
    )

    result = filter_engine.filter([signal], config=config)

    assert result.kept_signals == []
    assert "region_mismatch" in result.excluded_signals[0].reasons


def test_relevance_filter_does_not_fail_on_missing_region_metadata() -> None:
    filter_engine = SignalRelevanceFilter()
    config = make_config()
    signal = make_normalized_signal(
        source_signal_id="5",
        title="AI workflow for clinics",
        topic_candidate="AI workflow for clinics",
        raw_text="CEO and CTO playbook for clinic automation",
        tags=["ceo"],
        metadata={},
    )

    result = filter_engine.filter([signal], config=config)

    assert [item.source_signal_id for item in result.kept_signals] == ["5"]
