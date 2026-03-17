from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    niche: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    icp: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    regions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    seeds: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    negatives: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RunSource(Base):
    __tablename__ = "run_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RawSignal(Base):
    __tablename__ = "raw_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_signal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    engagement_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    canonical_topic: Mapped[str] = mapped_column(String(512), nullable=False)
    cluster_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_urls_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ContentCandidate(Base):
    __tablename__ = "content_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    topic_cluster_id: Mapped[int] = mapped_column(
        ForeignKey("topic_clusters.id"),
        nullable=False,
        index=True,
    )
    trend_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    why_now: Mapped[str | None] = mapped_column(Text, nullable=True)
    angles_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TopicLabelLink(Base):
    __tablename__ = "topic_label_links"
    __table_args__ = (UniqueConstraint("topic_cluster_id", "label_id", name="uq_topic_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_cluster_id: Mapped[int] = mapped_column(
        ForeignKey("topic_clusters.id"),
        nullable=False,
        index=True,
    )
    label_id: Mapped[int] = mapped_column(ForeignKey("labels.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
