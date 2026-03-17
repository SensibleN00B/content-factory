from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.domain.processing.normalizer import NormalizedSignal

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class DeduplicationResult:
    unique_signals: list[NormalizedSignal]
    dropped_signals: list[NormalizedSignal]
    dropped_by_rule: dict[str, int]


class SignalDeduplicator:
    def deduplicate(self, signals: list[NormalizedSignal]) -> DeduplicationResult:
        seen_hashes = {
            "url": set(),
            "title": set(),
            "topic": set(),
        }
        dropped_by_rule = {
            "url": 0,
            "title": 0,
            "topic": 0,
        }
        unique_signals: list[NormalizedSignal] = []
        dropped_signals: list[NormalizedSignal] = []

        for signal in signals:
            fingerprints = self._build_fingerprints(signal)

            duplicate_rule: str | None = None
            for rule in ("url", "title", "topic"):
                fingerprint = fingerprints[rule]
                if fingerprint is not None and fingerprint in seen_hashes[rule]:
                    duplicate_rule = rule
                    break

            if duplicate_rule is not None:
                dropped_by_rule[duplicate_rule] += 1
                dropped_signals.append(signal)
                continue

            unique_signals.append(signal)
            for rule in ("url", "title", "topic"):
                fingerprint = fingerprints[rule]
                if fingerprint is not None:
                    seen_hashes[rule].add(fingerprint)

        return DeduplicationResult(
            unique_signals=unique_signals,
            dropped_signals=dropped_signals,
            dropped_by_rule=dropped_by_rule,
        )

    def _build_fingerprints(self, signal: NormalizedSignal) -> dict[str, str | None]:
        return {
            "url": self._hash_if_present(self._normalize_url_for_hash(signal.url)),
            "title": self._hash_if_present(self._normalize_text_for_hash(signal.title)),
            "topic": self._hash_if_present(self._normalize_text_for_hash(signal.topic_candidate)),
        }

    @staticmethod
    def _hash_if_present(value: str | None) -> str | None:
        if value is None:
            return None
        return hashlib.sha1(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_url_for_hash(url: str | None) -> str | None:
        if url is None:
            return None
        normalized = url.strip().lower()
        while normalized.endswith("/"):
            normalized = normalized[:-1]
        return normalized or None

    @staticmethod
    def _normalize_text_for_hash(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _WHITESPACE_RE.sub(" ", value).strip().lower()
        return normalized or None
