from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileIn(BaseModel):
    niche: list[str] = Field(default_factory=list)
    icp: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    language: str
    seeds: list[str] = Field(default_factory=list)
    negatives: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
