from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LabelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
