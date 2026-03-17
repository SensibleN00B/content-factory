from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RunOut(BaseModel):
    id: int
    profile_id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    input_snapshot: dict[str, Any] | None
    error_summary: str | None
    created_at: datetime
