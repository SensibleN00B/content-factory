from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.processing.normalizer import NormalizedSignal


@dataclass
class RelevanceFilterConfig:
    niche_terms: list[str] = field(default_factory=list)
    icp_terms: list[str] = field(default_factory=list)
    allowed_regions: list[str] = field(default_factory=list)
    language: str | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.niche_terms = _normalize_terms(self.niche_terms)
        self.icp_terms = _normalize_terms(self.icp_terms)
        self.allowed_regions = _normalize_regions(self.allowed_regions)
        self.include_keywords = _normalize_terms(self.include_keywords)
        self.exclude_keywords = _normalize_terms(self.exclude_keywords)
        self.language = _normalize_language(self.language)


@dataclass(frozen=True)
class ExcludedSignal:
    signal: NormalizedSignal
    reasons: list[str]


@dataclass(frozen=True)
class RelevanceFilterResult:
    kept_signals: list[NormalizedSignal]
    excluded_signals: list[ExcludedSignal]


class SignalRelevanceFilter:
    def filter(
        self,
        signals: list[NormalizedSignal],
        *,
        config: RelevanceFilterConfig,
    ) -> RelevanceFilterResult:
        kept_signals: list[NormalizedSignal] = []
        excluded_signals: list[ExcludedSignal] = []

        for signal in signals:
            reasons = self._collect_reasons(signal=signal, config=config)
            if reasons:
                excluded_signals.append(ExcludedSignal(signal=signal, reasons=reasons))
                continue
            kept_signals.append(signal)

        return RelevanceFilterResult(
            kept_signals=kept_signals,
            excluded_signals=excluded_signals,
        )

    def _collect_reasons(
        self,
        *,
        signal: NormalizedSignal,
        config: RelevanceFilterConfig,
    ) -> list[str]:
        reasons: list[str] = []
        haystack = _build_haystack(signal)

        if config.exclude_keywords and _matches_any(haystack, config.exclude_keywords):
            reasons.append("contains_excluded_keyword")
        if config.include_keywords and not _matches_any(haystack, config.include_keywords):
            reasons.append("missing_include_keyword")
        if config.niche_terms and not _matches_any(haystack, config.niche_terms):
            reasons.append("missing_niche_match")
        if config.icp_terms and not _matches_any(haystack, config.icp_terms):
            reasons.append("missing_icp_match")
        if _language_mismatch(signal=signal, expected_language=config.language):
            reasons.append("language_mismatch")
        if _region_mismatch(signal=signal, allowed_regions=config.allowed_regions):
            reasons.append("region_mismatch")

        return reasons


def _normalize_terms(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        term = value.strip().lower()
        if not term or term in seen:
            continue
        seen.add(term)
        normalized.append(term)
    return normalized


def _normalize_regions(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        region = value.strip().upper()
        if not region or region in seen:
            continue
        seen.add(region)
        normalized.append(region)
    return normalized


def _normalize_language(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _build_haystack(signal: NormalizedSignal) -> str:
    fragments = [
        signal.query or "",
        signal.title or "",
        signal.topic_candidate or "",
        signal.raw_text or "",
        " ".join(signal.tags),
    ]
    return " ".join(fragment.lower() for fragment in fragments if fragment).strip()


def _matches_any(haystack: str, terms: list[str]) -> bool:
    return any(term in haystack for term in terms)


def _language_mismatch(*, signal: NormalizedSignal, expected_language: str | None) -> bool:
    if expected_language is None:
        return False
    if signal.language is None:
        return False
    return signal.language.strip().lower() != expected_language


def _region_mismatch(*, signal: NormalizedSignal, allowed_regions: list[str]) -> bool:
    if not allowed_regions:
        return False

    signal_regions = _extract_regions(signal.metadata)
    if not signal_regions:
        return False

    return signal_regions.isdisjoint(set(allowed_regions))


def _extract_regions(metadata: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("region", "geo", "country"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            values.add(value.strip().upper())

    regions = metadata.get("regions")
    if isinstance(regions, list):
        for item in regions:
            if isinstance(item, str) and item.strip():
                values.add(item.strip().upper())

    return values
