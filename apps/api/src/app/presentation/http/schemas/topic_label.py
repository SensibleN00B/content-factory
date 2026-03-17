from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TopicLabelAssignIn(BaseModel):
    label: str


class TopicLabelOut(BaseModel):
    topic_cluster_id: int
    label: str
    created_at: datetime
