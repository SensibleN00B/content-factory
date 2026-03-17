from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from time import perf_counter
from typing import Literal

from app.domain.ingestion.connectors import (
    SourceCollectedSignal,
    SourceCollectRequest,
    SourceConnector,
)
from app.domain.ingestion.registry import SourceNotRegisteredError, SourceRegistry

RunStatus = Literal["success", "failed", "timeout"]


@dataclass(frozen=True)
class SourceExecutionPolicy:
    timeout_seconds: float = 15.0
    max_retries: int = 1
    retry_delay_seconds: float = 0.0


@dataclass(frozen=True)
class SourceRunResult:
    source_key: str
    status: RunStatus
    attempts: int
    duration_ms: int
    signals: list[SourceCollectedSignal] = field(default_factory=list)
    error_message: str | None = None


@dataclass(frozen=True)
class IngestionRunSummary:
    results: dict[str, SourceRunResult]
    collected_signals: list[SourceCollectedSignal]


class SourceTimeoutError(TimeoutError):
    """Raised when source execution exceeds timeout."""


class IngestionRunner:
    def __init__(
        self, *, registry: SourceRegistry, policy: SourceExecutionPolicy | None = None
    ) -> None:
        self._registry = registry
        self._policy = policy or SourceExecutionPolicy()

    def run_sources(
        self,
        *,
        request: SourceCollectRequest,
        sources: list[str] | None = None,
    ) -> IngestionRunSummary:
        source_keys = sources or list(self._registry.list_sources())

        results: dict[str, SourceRunResult] = {}
        collected_signals: list[SourceCollectedSignal] = []

        for source_key in source_keys:
            try:
                connector = self._registry.get(source_key)
            except SourceNotRegisteredError as exc:
                results[source_key] = SourceRunResult(
                    source_key=source_key,
                    status="failed",
                    attempts=0,
                    duration_ms=0,
                    signals=[],
                    error_message=str(exc),
                )
                continue

            result = self._run_single_source(
                source_key=source_key,
                connector=connector,
                request=request,
            )
            results[source_key] = result
            if result.status == "success":
                collected_signals.extend(result.signals)

        return IngestionRunSummary(results=results, collected_signals=collected_signals)

    def _run_single_source(
        self,
        *,
        source_key: str,
        connector: SourceConnector,
        request: SourceCollectRequest,
    ) -> SourceRunResult:
        total_start = perf_counter()
        attempts = 0
        last_status: RunStatus = "failed"
        last_error: str | None = None

        max_attempts = self._policy.max_retries + 1

        while attempts < max_attempts:
            attempts += 1
            try:
                signals = self._collect_with_timeout(
                    source_key=source_key,
                    connector=connector,
                    request=request,
                    timeout_seconds=self._policy.timeout_seconds,
                )
                duration_ms = int((perf_counter() - total_start) * 1000)
                return SourceRunResult(
                    source_key=source_key,
                    status="success",
                    attempts=attempts,
                    duration_ms=duration_ms,
                    signals=signals,
                    error_message=None,
                )
            except SourceTimeoutError as exc:
                last_status = "timeout"
                last_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                last_status = "failed"
                last_error = str(exc)

            if attempts < max_attempts and self._policy.retry_delay_seconds > 0:
                time.sleep(self._policy.retry_delay_seconds)

        duration_ms = int((perf_counter() - total_start) * 1000)
        return SourceRunResult(
            source_key=source_key,
            status=last_status,
            attempts=attempts,
            duration_ms=duration_ms,
            signals=[],
            error_message=last_error,
        )

    @staticmethod
    def _collect_with_timeout(
        *,
        source_key: str,
        connector: SourceConnector,
        request: SourceCollectRequest,
        timeout_seconds: float,
    ) -> list[SourceCollectedSignal]:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(connector.collect, request)
            try:
                result = future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                future.cancel()
                raise SourceTimeoutError(
                    f"Source '{source_key}' timed out after {timeout_seconds} seconds"
                ) from exc

        return result
