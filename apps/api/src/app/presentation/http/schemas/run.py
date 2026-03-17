from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunSourceOut(BaseModel):
    source: str
    status: str
    fetched_count: int
    error_text: str | None
    duration_ms: int | None
    created_at: datetime


class RunOut(BaseModel):
    id: int
    profile_id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    input_snapshot: dict[str, Any] | None
    error_summary: str | None
    created_at: datetime
    sources: list[RunSourceOut] = Field(default_factory=list)
