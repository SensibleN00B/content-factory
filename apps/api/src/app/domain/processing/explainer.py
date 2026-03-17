from __future__ import annotations

from dataclasses import dataclass

from app.domain.processing.clusterer import TopicClusterDraft
from app.domain.processing.scorer import ScoredTopicCandidate


@dataclass(frozen=True)
class ExplainabilityConfig:
    max_evidence_links: int = 3
    max_angles: int = 3


@dataclass(frozen=True)
class ExplainedTopicCandidate:
    cluster_key: str
    canonical_topic: str
    trend_score: float
    score_breakdown: dict[str, float]
    source_count: int
    signal_count: int
    why_now: str
    evidence_links: list[str]
    angles: list[str]


class TopicExplainer:
    def explain(
        self,
        candidates: list[ScoredTopicCandidate],
        *,
        clusters_by_key: dict[str, TopicClusterDraft],
        config: ExplainabilityConfig | None = None,
    ) -> list[ExplainedTopicCandidate]:
        cfg = config or ExplainabilityConfig()
        explained: list[ExplainedTopicCandidate] = []

        for candidate in candidates:
            cluster = clusters_by_key.get(candidate.cluster_key)
            evidence_links = self._build_evidence_links(
                candidate=candidate,
                cluster=cluster,
                max_links=cfg.max_evidence_links,
            )
            why_now = self._build_why_now(candidate=candidate)
            angles = self._build_angles(candidate=candidate, max_angles=cfg.max_angles)
            explained.append(
                ExplainedTopicCandidate(
                    cluster_key=candidate.cluster_key,
                    canonical_topic=candidate.canonical_topic,
                    trend_score=candidate.trend_score,
                    score_breakdown=dict(candidate.score_breakdown),
                    source_count=candidate.source_count,
                    signal_count=candidate.signal_count,
                    why_now=why_now,
                    evidence_links=evidence_links,
                    angles=angles,
                )
            )

        return explained

    def _build_why_now(self, *, candidate: ScoredTopicCandidate) -> str:
        sorted_components = sorted(
            candidate.score_breakdown.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        top_components = [name for name, _ in sorted_components[:2]]
        if len(top_components) == 2:
            component_text = f"{top_components[0]} and {top_components[1]}"
        elif top_components:
            component_text = top_components[0]
        else:
            component_text = "multi-signal"

        return (
            f"Strong {component_text} signal now: "
            f"{candidate.signal_count} signals across {candidate.source_count} sources."
        )

    def _build_evidence_links(
        self,
        *,
        candidate: ScoredTopicCandidate,
        cluster: TopicClusterDraft | None,
        max_links: int,
    ) -> list[str]:
        if cluster is not None:
            raw_links = list(cluster.evidence_urls)
        else:
            raw_links = list(candidate.evidence_urls)

        links: list[str] = []
        seen: set[str] = set()
        for url in raw_links:
            if url in seen:
                continue
            seen.add(url)
            links.append(url)
            if len(links) >= max_links:
                break
        return links

    def _build_angles(self, *, candidate: ScoredTopicCandidate, max_angles: int) -> list[str]:
        topic = candidate.canonical_topic
        options = [
            f"How teams use {topic} to cut execution bottlenecks",
            f"Why {topic} fails in real implementations and how to avoid it",
            f"What founders misunderstand about {topic}",
            f"{topic}: pragmatic playbook for first 30 days",
        ]
        return options[: max(max_angles, 0)]
