from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CandidateOut(BaseModel):
    id: int
    run_id: int
    topic_cluster_id: int
    canonical_topic: str
    source_count: int
    signal_count: int
    trend_score: float
    why_now: str | None
    labels: list[str]
    created_at: datetime


class CandidateDetailOut(CandidateOut):
    score_breakdown: dict[str, Any]
    evidence_urls: list[str]
    angles: list[str]
    confidence: float | None
