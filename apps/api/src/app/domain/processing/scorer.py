from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.processing.clusterer import TopicClusterDraft


@dataclass(frozen=True)
class ScoringWeights:
    velocity: float = 0.25
    volume: float = 0.20
    engagement: float = 0.20
    relevance: float = 0.25
    opinionability: float = 0.10

    def normalized(self) -> ScoringWeights:
        raw_values = {
            "velocity": max(self.velocity, 0.0),
            "volume": max(self.volume, 0.0),
            "engagement": max(self.engagement, 0.0),
            "relevance": max(self.relevance, 0.0),
            "opinionability": max(self.opinionability, 0.0),
        }
        total = sum(raw_values.values())
        if total <= 0:
            return ScoringWeights()
        return ScoringWeights(
            velocity=raw_values["velocity"] / total,
            volume=raw_values["volume"] / total,
            engagement=raw_values["engagement"] / total,
            relevance=raw_values["relevance"] / total,
            opinionability=raw_values["opinionability"] / total,
        )


@dataclass(frozen=True)
class ScoringConfig:
    relevance_terms: list[str] = field(default_factory=list)
    reference_time: datetime | None = None
    weights: ScoringWeights = field(default_factory=ScoringWeights)

    def normalized_relevance_terms(self) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for term in self.relevance_terms:
            value = term.strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized


@dataclass(frozen=True)
class ScoredTopicCandidate:
    cluster_key: str
    canonical_topic: str
    trend_score: float
    score_breakdown: dict[str, float]
    source_count: int
    signal_count: int
    evidence_urls: list[str]


class TopicScorer:
    def score_clusters(
        self,
        clusters: list[TopicClusterDraft],
        *,
        config: ScoringConfig,
    ) -> list[ScoredTopicCandidate]:
        reference_time = config.reference_time or datetime.now(tz=UTC)
        weights = config.weights.normalized()
        relevance_terms = config.normalized_relevance_terms()

        candidates: list[ScoredTopicCandidate] = []
        for cluster in clusters:
            breakdown = {
                "velocity": self._score_velocity(cluster, reference_time=reference_time),
                "volume": self._score_volume(cluster),
                "engagement": self._score_engagement(cluster),
                "relevance": self._score_relevance(cluster, relevance_terms=relevance_terms),
                "opinionability": self._score_opinionability(cluster),
            }
            total_score = (
                breakdown["velocity"] * weights.velocity
                + breakdown["volume"] * weights.volume
                + breakdown["engagement"] * weights.engagement
                + breakdown["relevance"] * weights.relevance
                + breakdown["opinionability"] * weights.opinionability
            )
            candidates.append(
                ScoredTopicCandidate(
                    cluster_key=cluster.cluster_key,
                    canonical_topic=cluster.canonical_topic,
                    trend_score=round(_clamp(total_score), 2),
                    score_breakdown={k: round(v, 2) for k, v in breakdown.items()},
                    source_count=cluster.source_count,
                    signal_count=cluster.signal_count,
                    evidence_urls=list(cluster.evidence_urls),
                )
            )

        candidates.sort(key=lambda item: (-item.trend_score, item.canonical_topic.lower()))
        return candidates

    def _score_velocity(self, cluster: TopicClusterDraft, *, reference_time: datetime) -> float:
        published: list[datetime] = []
        for signal in cluster.signals:
            if signal.published_at is None:
                continue
            published_at = signal.published_at
            if published_at.tzinfo is None or published_at.tzinfo.utcoffset(published_at) is None:
                published_at = published_at.replace(tzinfo=UTC)
            published.append(published_at.astimezone(UTC))

        if not published:
            return 40.0

        ages_hours = [(reference_time - date).total_seconds() / 3600 for date in published]
        avg_age = sum(ages_hours) / len(ages_hours)
        score = 100.0 - (avg_age * 1.2)
        return _clamp(score)

    @staticmethod
    def _score_volume(cluster: TopicClusterDraft) -> float:
        score = (cluster.signal_count * 20.0) + (cluster.source_count * 10.0)
        return _clamp(score)

    @staticmethod
    def _score_engagement(cluster: TopicClusterDraft) -> float:
        totals = [max(signal.engagement.get("total", 0), 0) for signal in cluster.signals]
        if not totals:
            return 0.0
        average = sum(totals) / len(totals)
        score = math.log10(average + 1.0) * 35.0
        return _clamp(score)

    def _score_relevance(self, cluster: TopicClusterDraft, *, relevance_terms: list[str]) -> float:
        if not relevance_terms:
            return 50.0

        haystack = self._build_haystack(cluster).lower()
        matches = sum(1 for term in relevance_terms if term in haystack)
        score = (matches / len(relevance_terms)) * 100.0
        return _clamp(score)

    def _score_opinionability(self, cluster: TopicClusterDraft) -> float:
        cues = [
            "why",
            "vs",
            "best",
            "worst",
            "mistake",
            "future",
            "should",
            "fail",
            "problem",
            "myth",
            "question",
            "how",
        ]
        haystack = self._build_haystack(cluster).lower()
        matches = sum(1 for cue in cues if cue in haystack)
        score = 20.0 + min(matches * 15.0, 80.0)
        if "?" in haystack:
            score += 10.0
        return _clamp(score)

    @staticmethod
    def _build_haystack(cluster: TopicClusterDraft) -> str:
        raw_texts = " ".join(signal.raw_text for signal in cluster.signals if signal.raw_text)
        return f"{cluster.canonical_topic} {raw_texts}".strip()


def _clamp(value: float, *, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))
