from __future__ import annotations

from dataclasses import dataclass

from app.domain.ingestion.connectors import SourceCollectRequest
from app.domain.ingestion.runner import IngestionRunner, IngestionRunSummary
from app.domain.processing.clusterer import SignalClusterer, TopicClusterDraft
from app.domain.processing.deduplicator import DeduplicationResult, SignalDeduplicator
from app.domain.processing.explainer import (
    ExplainabilityConfig,
    ExplainedTopicCandidate,
    TopicExplainer,
)
from app.domain.processing.normalizer import NormalizedSignal, SignalNormalizer
from app.domain.processing.relevance_filter import (
    RelevanceFilterConfig,
    RelevanceFilterResult,
    SignalRelevanceFilter,
)
from app.domain.processing.scorer import ScoredTopicCandidate, ScoringConfig, TopicScorer


@dataclass(frozen=True)
class TrendPipelineResult:
    run_summary: IngestionRunSummary
    normalized_signals: list[NormalizedSignal]
    deduplication: DeduplicationResult
    relevance: RelevanceFilterResult
    clusters: list[TopicClusterDraft]
    scored_candidates: list[ScoredTopicCandidate]
    explained_candidates: list[ExplainedTopicCandidate]


class TrendPipeline:
    def __init__(
        self,
        *,
        runner: IngestionRunner,
        normalizer: SignalNormalizer,
        relevance_filter: SignalRelevanceFilter,
        scorer: TopicScorer,
        explainer: TopicExplainer,
        deduplicator: SignalDeduplicator | None = None,
        clusterer: SignalClusterer | None = None,
    ) -> None:
        self._runner = runner
        self._normalizer = normalizer
        self._deduplicator = deduplicator or SignalDeduplicator()
        self._clusterer = clusterer or SignalClusterer()
        self._relevance_filter = relevance_filter
        self._scorer = scorer
        self._explainer = explainer

    def run(
        self,
        *,
        request: SourceCollectRequest,
        relevance_config: RelevanceFilterConfig,
        scoring_config: ScoringConfig,
        explainability_config: ExplainabilityConfig | None = None,
        sources: list[str] | None = None,
        top_k: int = 20,
    ) -> TrendPipelineResult:
        run_summary = self._runner.run_sources(request=request, sources=sources)

        normalized_signals = self._normalizer.normalize_many(run_summary.collected_signals)
        deduplication = self._deduplicator.deduplicate(normalized_signals)
        relevance = self._relevance_filter.filter(
            deduplication.unique_signals,
            config=relevance_config,
        )
        clusters = self._clusterer.cluster(relevance.kept_signals)

        scored_candidates = self._scorer.score_clusters(clusters, config=scoring_config)
        if top_k > 0:
            scored_candidates = scored_candidates[:top_k]

        clusters_by_key = {cluster.cluster_key: cluster for cluster in clusters}
        explained_candidates = self._explainer.explain(
            scored_candidates,
            clusters_by_key=clusters_by_key,
            config=explainability_config,
        )

        return TrendPipelineResult(
            run_summary=run_summary,
            normalized_signals=normalized_signals,
            deduplication=deduplication,
            relevance=relevance,
            clusters=clusters,
            scored_candidates=scored_candidates,
            explained_candidates=explained_candidates,
        )
