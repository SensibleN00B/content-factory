from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SourceCollectRequest:
    keywords: list[str]
    regions: list[str]
    language: str
    limit: int = 50


@dataclass(frozen=True)
class SourceCollectedSignal:
    source: str
    source_signal_id: str | None
    title: str | None
    url: str | None
    published_at: datetime | None
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    engagement: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SourceConnector(Protocol):
    source_key: str

    def collect(self, request: SourceCollectRequest) -> list[SourceCollectedSignal]: ...
