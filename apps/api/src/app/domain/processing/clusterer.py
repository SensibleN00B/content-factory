from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from app.domain.processing.normalizer import NormalizedSignal

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class TopicClusterDraft:
    cluster_key: str
    canonical_topic: str
    signals: list[NormalizedSignal]
    source_count: int
    signal_count: int
    evidence_urls: list[str]


@dataclass
class _ClusterBucket:
    canonical_topic: str
    signals: list[NormalizedSignal] = field(default_factory=list)
    tokens: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    evidence_urls: list[str] = field(default_factory=list)

    def add(self, signal: NormalizedSignal, tokens: set[str]) -> None:
        self.signals.append(signal)
        self.tokens.update(tokens)
        self.sources.add(signal.source)
        if signal.url is not None and signal.url not in self.evidence_urls:
            self.evidence_urls.append(signal.url)


class SignalClusterer:
    def __init__(self, *, min_token_overlap: int = 2) -> None:
        self._min_token_overlap = min_token_overlap
        self._stopwords = {
            "a",
            "an",
            "and",
            "for",
            "in",
            "of",
            "on",
            "the",
            "to",
            "with",
        }
        self._synonyms = {
            "assistant": "receptionist",
            "agent": "receptionist",
            "phone": "voice",
        }

    def cluster(self, signals: list[NormalizedSignal]) -> list[TopicClusterDraft]:
        buckets: list[_ClusterBucket] = []

        for signal in signals:
            topic_text = self._extract_topic_text(signal)
            tokens = self._tokenize(topic_text)
            if not tokens:
                tokens = {"misc"}

            bucket = self._find_matching_bucket(buckets=buckets, tokens=tokens)
            if bucket is None:
                bucket = _ClusterBucket(canonical_topic=topic_text)
                buckets.append(bucket)
            bucket.add(signal, tokens)

        return [
            TopicClusterDraft(
                cluster_key=self._build_cluster_key(bucket.tokens),
                canonical_topic=bucket.canonical_topic,
                signals=list(bucket.signals),
                source_count=len(bucket.sources),
                signal_count=len(bucket.signals),
                evidence_urls=list(bucket.evidence_urls),
            )
            for bucket in buckets
        ]

    def _find_matching_bucket(
        self, *, buckets: list[_ClusterBucket], tokens: set[str]
    ) -> _ClusterBucket | None:
        best_bucket: _ClusterBucket | None = None
        best_overlap = 0

        for bucket in buckets:
            overlap = len(tokens.intersection(bucket.tokens))
            if overlap < self._min_token_overlap:
                continue
            if overlap > best_overlap:
                best_overlap = overlap
                best_bucket = bucket

        return best_bucket

    def _extract_topic_text(self, signal: NormalizedSignal) -> str:
        candidate = signal.topic_candidate or signal.title or signal.query or signal.raw_text
        normalized = _WHITESPACE_RE.sub(" ", candidate or "").strip()
        return normalized or "Untitled topic"

    def _tokenize(self, value: str) -> set[str]:
        tokens: set[str] = set()
        for match in _TOKEN_RE.findall(value.lower()):
            token = self._normalize_token(match)
            if token and token not in self._stopwords:
                tokens.add(token)
        return tokens

    def _normalize_token(self, token: str) -> str:
        normalized = self._synonyms.get(token, token)
        if len(normalized) > 3 and normalized.endswith("s"):
            normalized = normalized[:-1]
        return normalized

    @staticmethod
    def _build_cluster_key(tokens: set[str]) -> str:
        payload = "|".join(sorted(tokens))
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
