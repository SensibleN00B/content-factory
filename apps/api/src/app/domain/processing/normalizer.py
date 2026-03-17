from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.domain.ingestion.connectors import SourceCollectedSignal

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedSignal:
    source: str
    source_signal_id: str | None
    query: str | None
    title: str | None
    topic_candidate: str | None
    url: str | None
    published_at: datetime | None
    raw_text: str
    engagement: dict[str, int]
    author: str | None
    tags: list[str]
    language: str | None
    metadata: dict[str, Any]
    raw_payload: dict[str, Any]


class SignalNormalizer:
    def normalize(self, signal: SourceCollectedSignal) -> NormalizedSignal:
        title = self._normalize_text(signal.title)
        query = self._extract_query(signal.metadata)
        raw_text = self._extract_raw_text(signal)

        return NormalizedSignal(
            source=signal.source.strip(),
            source_signal_id=signal.source_signal_id,
            query=query,
            title=title,
            topic_candidate=title or self._derive_topic_candidate(raw_text),
            url=self._normalize_url(signal.url),
            published_at=self._normalize_datetime(signal.published_at),
            raw_text=raw_text,
            engagement=self._normalize_engagement(signal.engagement),
            author=self._normalize_text(signal.metadata.get("author")),
            tags=self._extract_tags(signal.metadata.get("tags")),
            language=self._extract_language(signal.metadata),
            metadata=dict(signal.metadata),
            raw_payload=dict(signal.raw_payload),
        )

    def normalize_many(self, signals: list[SourceCollectedSignal]) -> list[NormalizedSignal]:
        return [self.normalize(signal) for signal in signals]

    def _extract_raw_text(self, signal: SourceCollectedSignal) -> str:
        payload_candidates = self._extract_payload_text_candidates(signal.raw_payload)
        for candidate in payload_candidates:
            text = self._normalize_text(candidate)
            if text is not None:
                return text

        title = self._normalize_text(signal.title)
        if title is not None:
            return title

        return ""

    def _extract_payload_text_candidates(self, payload: dict[str, Any]) -> list[Any]:
        candidates: list[Any] = []

        for key in ("selftext", "text", "body", "summary", "description", "tagline"):
            if key in payload:
                candidates.append(payload.get(key))

        snippet = payload.get("snippet")
        if isinstance(snippet, dict):
            candidates.extend([snippet.get("description"), snippet.get("title")])
        elif snippet is not None:
            candidates.append(snippet)

        title = payload.get("title")
        if isinstance(title, dict):
            candidates.append(title.get("query"))
        else:
            candidates.append(title)

        return candidates

    @staticmethod
    def _derive_topic_candidate(raw_text: str) -> str | None:
        text = raw_text.strip()
        if not text:
            return None
        if len(text) <= 80:
            return text
        shortened = text[:80].rstrip()
        return f"{shortened}..."

    @staticmethod
    def _extract_query(metadata: dict[str, Any]) -> str | None:
        query = SignalNormalizer._normalize_text(metadata.get("query"))
        if query is not None:
            return query
        return SignalNormalizer._normalize_text(metadata.get("query_match"))

    @staticmethod
    def _normalize_url(url: str | None) -> str | None:
        if url is None:
            return None
        normalized = url.strip()
        return normalized or None

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _extract_tags(raw_tags: Any) -> list[str]:
        if raw_tags is None:
            return []

        if isinstance(raw_tags, str):
            raw_items = [raw_tags]
        elif isinstance(raw_tags, list):
            raw_items = raw_tags
        else:
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            text = SignalNormalizer._normalize_text(item)
            if text is None:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(lowered)
        return normalized

    @staticmethod
    def _extract_language(metadata: dict[str, Any]) -> str | None:
        language = SignalNormalizer._normalize_text(metadata.get("language"))
        if language is None:
            return None
        return language.lower()

    @staticmethod
    def _normalize_engagement(engagement: dict[str, Any]) -> dict[str, int]:
        alias_groups = {
            "votes": ("upvotes", "score", "points", "votes", "likes"),
            "comments": ("comments", "num_comments"),
            "views": ("views", "view_count", "viewCount"),
            "search_traffic": ("search_traffic", "searchTraffic"),
        }

        normalized = {
            key: sum(
                SignalNormalizer._to_non_negative_int(engagement.get(alias)) for alias in aliases
            )
            for key, aliases in alias_groups.items()
        }
        normalized["total"] = sum(
            normalized[key] for key in ("votes", "comments", "views", "search_traffic")
        )
        return normalized

    @staticmethod
    def _to_non_negative_int(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            return max(int(value), 0)
        if not isinstance(value, str):
            return 0

        text = value.strip().replace(",", "").upper()
        if not text:
            return 0

        multiplier = 1
        if text.endswith("+"):
            text = text[:-1]
        if text.endswith("K"):
            multiplier = 1_000
            text = text[:-1]
        elif text.endswith("M"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith("B"):
            multiplier = 1_000_000_000
            text = text[:-1]

        try:
            number = float(text)
        except ValueError:
            digits_only = "".join(ch for ch in text if ch.isdigit())
            if not digits_only:
                return 0
            number = float(digits_only)

        return max(int(number * multiplier), 0)

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        decoded = html.unescape(value)
        without_tags = _HTML_TAG_RE.sub(" ", decoded)
        normalized = _WHITESPACE_RE.sub(" ", without_tags).strip()
        return normalized or None
