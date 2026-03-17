from __future__ import annotations

from collections.abc import Iterable

from app.domain.ingestion.connectors import SourceConnector


class SourceNotRegisteredError(LookupError):
    """Raised when source connector is missing in registry."""


class DuplicateSourceConnectorError(ValueError):
    """Raised when trying to register already registered source key."""


class SourceRegistry:
    def __init__(self, connectors: Iterable[SourceConnector] | None = None) -> None:
        self._connectors: dict[str, SourceConnector] = {}

        for connector in connectors or ():
            self.register(connector)

    def register(self, connector: SourceConnector) -> None:
        source_key = connector.source_key.strip().lower()
        if not source_key:
            raise ValueError("Source connector key cannot be empty")

        if source_key in self._connectors:
            raise DuplicateSourceConnectorError(
                f"Source connector '{source_key}' is already registered"
            )

        self._connectors[source_key] = connector

    def get(self, source_key: str) -> SourceConnector:
        normalized = source_key.strip().lower()
        try:
            return self._connectors[normalized]
        except KeyError as exc:
            raise SourceNotRegisteredError(
                f"Source connector '{normalized}' is not registered"
            ) from exc

    def has(self, source_key: str) -> bool:
        normalized = source_key.strip().lower()
        return normalized in self._connectors

    def list_sources(self) -> tuple[str, ...]:
        return tuple(sorted(self._connectors.keys()))
