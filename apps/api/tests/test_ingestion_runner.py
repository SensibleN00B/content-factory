from __future__ import annotations

import time

from app.domain.ingestion.connectors import SourceCollectedSignal, SourceCollectRequest
from app.domain.ingestion.registry import SourceRegistry


def make_request() -> SourceCollectRequest:
    return SourceCollectRequest(
        keywords=["ai", "automation"],
        regions=["US"],
        language="en",
        limit=5,
    )


def make_signal(*, source: str, signal_id: str) -> SourceCollectedSignal:
    return SourceCollectedSignal(
        source=source,
        source_signal_id=signal_id,
        title=f"{source}-{signal_id}",
        url=f"https://example.com/{source}/{signal_id}",
        published_at=None,
        raw_payload={"id": signal_id},
        metadata={},
        engagement={},
    )


def test_ingestion_runner_successfully_collects_from_all_sources() -> None:
    from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy

    class SourceA:
        source_key = "source_a"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [make_signal(source="source_a", signal_id="1")]

    class SourceB:
        source_key = "source_b"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [make_signal(source="source_b", signal_id="1")]

    registry = SourceRegistry(connectors=[SourceA(), SourceB()])
    runner = IngestionRunner(registry=registry, policy=SourceExecutionPolicy(timeout_seconds=0.2))

    summary = runner.run_sources(request=make_request(), sources=["source_a", "source_b"])

    assert summary.results["source_a"].status == "success"
    assert summary.results["source_b"].status == "success"
    assert len(summary.collected_signals) == 2


def test_ingestion_runner_retries_transient_error_and_succeeds() -> None:
    from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy

    class FlakySource:
        source_key = "flaky"

        def __init__(self) -> None:
            self.attempts = 0

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            self.attempts += 1
            if self.attempts < 2:
                raise RuntimeError("transient error")
            return [make_signal(source="flaky", signal_id="ok")]

    flaky = FlakySource()
    registry = SourceRegistry(connectors=[flaky])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.2, max_retries=2),
    )

    summary = runner.run_sources(request=make_request(), sources=["flaky"])

    assert summary.results["flaky"].status == "success"
    assert summary.results["flaky"].attempts == 2
    assert len(summary.collected_signals) == 1


def test_ingestion_runner_source_failure_does_not_break_other_sources() -> None:
    from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy

    class BrokenSource:
        source_key = "broken"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            raise ValueError("broken source")

    class HealthySource:
        source_key = "healthy"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [make_signal(source="healthy", signal_id="1")]

    registry = SourceRegistry(connectors=[BrokenSource(), HealthySource()])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.2, max_retries=1),
    )

    summary = runner.run_sources(request=make_request(), sources=["broken", "healthy"])

    assert summary.results["broken"].status == "failed"
    assert summary.results["broken"].attempts == 2
    assert "broken source" in (summary.results["broken"].error_message or "")
    assert summary.results["healthy"].status == "success"
    assert len(summary.collected_signals) == 1


def test_ingestion_runner_timeout_does_not_break_other_sources() -> None:
    from app.domain.ingestion.runner import IngestionRunner, SourceExecutionPolicy

    class SlowSource:
        source_key = "slow"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            time.sleep(0.05)
            return [make_signal(source="slow", signal_id="1")]

    class FastSource:
        source_key = "fast"

        def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]:
            return [make_signal(source="fast", signal_id="1")]

    registry = SourceRegistry(connectors=[SlowSource(), FastSource()])
    runner = IngestionRunner(
        registry=registry,
        policy=SourceExecutionPolicy(timeout_seconds=0.01, max_retries=0),
    )

    summary = runner.run_sources(request=make_request(), sources=["slow", "fast"])

    assert summary.results["slow"].status == "timeout"
    assert "timed out" in (summary.results["slow"].error_message or "")
    assert summary.results["fast"].status == "success"
    assert len(summary.collected_signals) == 1
