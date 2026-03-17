from __future__ import annotations

from datetime import UTC, datetime

import pytest


def test_registry_returns_registered_connector() -> None:
    from app.domain.ingestion.connectors import SourceCollectedSignal, SourceCollectRequest
    from app.domain.ingestion.registry import SourceRegistry

    class DummyConnector:
        source_key = "dummy"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [
                SourceCollectedSignal(
                    source=self.source_key,
                    source_signal_id="abc-1",
                    title="Dummy title",
                    url="https://example.com/item/abc-1",
                    published_at=datetime(2026, 3, 17, tzinfo=UTC),
                    raw_payload={"request_keywords": request.keywords},
                    metadata={"connector": self.source_key},
                    engagement={"upvotes": 1},
                )
            ]

    registry = SourceRegistry()
    connector = DummyConnector()
    registry.register(connector)

    resolved = registry.get("dummy")
    collected = resolved.collect(
        SourceCollectRequest(
            keywords=["ai agent"],
            regions=["US", "CA", "EU"],
            language="en",
        )
    )

    assert resolved is connector
    assert registry.list_sources() == ("dummy",)
    assert collected[0].source == "dummy"


def test_registry_rejects_duplicate_source_key() -> None:
    from app.domain.ingestion.registry import DuplicateSourceConnectorError, SourceRegistry

    class DummyConnector:
        source_key = "reddit"

        def collect(self, request: object) -> list[object]:
            return []

    registry = SourceRegistry()
    registry.register(DummyConnector())

    with pytest.raises(DuplicateSourceConnectorError):
        registry.register(DummyConnector())


def test_registry_raises_for_missing_source() -> None:
    from app.domain.ingestion.registry import SourceNotRegisteredError, SourceRegistry

    registry = SourceRegistry()

    with pytest.raises(SourceNotRegisteredError):
        registry.get("youtube")


def test_registry_supports_constructor_registration() -> None:
    from app.domain.ingestion.registry import SourceRegistry

    class RedditConnector:
        source_key = "reddit"

        def collect(self, request: object) -> list[object]:
            return []

    class HnConnector:
        source_key = "hackernews"

        def collect(self, request: object) -> list[object]:
            return []

    registry = SourceRegistry(connectors=[RedditConnector(), HnConnector()])

    assert registry.has("reddit") is True
    assert registry.has("hackernews") is True
    assert registry.list_sources() == ("hackernews", "reddit")
