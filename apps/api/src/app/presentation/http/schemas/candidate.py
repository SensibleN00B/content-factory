from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CandidateOut(BaseModel):
    id: int
    run_id: int
    topic_cluster_id: int
    canonical_topic: str
    trend_score: float
    why_now: str | None
    labels: list[str]
    created_at: datetime
