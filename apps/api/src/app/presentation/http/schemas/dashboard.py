from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardBriefingItemOut(BaseModel):
    kind: str
    title: str
    detail: str


class DashboardRecentTopicOut(BaseModel):
    candidate_id: int
    run_id: int
    canonical_topic: str
    trend_score: float
    movement: str
    why_now: str | None
    source_count: int
    signal_count: int
    labels: list[str] = Field(default_factory=list)
    created_at: datetime


class DashboardLatestRunOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    candidate_count: int


class DashboardPipelineStageOut(BaseModel):
    stage_key: str
    label: str
    input_count: int
    kept_count: int
    dropped_count: int
    drop_rate: float


class DashboardPipelineMetricsOut(BaseModel):
    stages: list[DashboardPipelineStageOut] = Field(default_factory=list)
    drop_reasons: dict[str, int] = Field(default_factory=dict)


class DashboardSourceHealthOut(BaseModel):
    total_sources: int
    healthy_sources: int
    failed_sources: int


class DashboardBriefingOut(BaseModel):
    generated_at: datetime
    briefing_available: bool
    briefing_unavailable_reason: str | None = None
    briefing_items: list[DashboardBriefingItemOut] = Field(default_factory=list)
    recent_topics: list[DashboardRecentTopicOut] = Field(default_factory=list)
    latest_run: DashboardLatestRunOut
    pipeline_metrics: DashboardPipelineMetricsOut
    source_health: DashboardSourceHealthOut
