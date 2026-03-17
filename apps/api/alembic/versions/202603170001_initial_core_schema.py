"""create initial core schema

Revision ID: 202603170001
Revises:
Create Date: 2026-03-17 00:00:00

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "202603170001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("niche", sa.JSON(), nullable=False),
        sa.Column("icp", sa.JSON(), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("seeds", sa.JSON(), nullable=True),
        sa.Column("negatives", sa.JSON(), nullable=True),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_profile_id", "runs", ["profile_id"])
    op.create_index("ix_runs_status", "runs", ["status"])

    op.create_table(
        "run_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_sources_run_id", "run_sources", ["run_id"])
    op.create_index("ix_run_sources_source", "run_sources", ["source"])

    op.create_table(
        "raw_signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_signal_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("engagement_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_signals_run_id", "raw_signals", ["run_id"])
    op.create_index("ix_raw_signals_source", "raw_signals", ["source"])
    op.create_index("ix_raw_signals_published_at", "raw_signals", ["published_at"])

    op.create_table(
        "topic_clusters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("canonical_topic", sa.String(length=512), nullable=False),
        sa.Column("cluster_hash", sa.String(length=128), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False),
        sa.Column("evidence_urls_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topic_clusters_run_id", "topic_clusters", ["run_id"])
    op.create_index("ix_topic_clusters_cluster_hash", "topic_clusters", ["cluster_hash"])

    op.create_table(
        "content_candidates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("topic_cluster_id", sa.Integer(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=True),
        sa.Column("why_now", sa.Text(), nullable=True),
        sa.Column("angles_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["topic_cluster_id"], ["topic_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_candidates_run_id", "content_candidates", ["run_id"])
    op.create_index("ix_content_candidates_topic_cluster_id", "content_candidates", ["topic_cluster_id"])

    op.create_table(
        "topic_label_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_cluster_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["label_id"], ["labels.id"]),
        sa.ForeignKeyConstraint(["topic_cluster_id"], ["topic_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_cluster_id", "label_id", name="uq_topic_label"),
    )
    op.create_index("ix_topic_label_links_topic_cluster_id", "topic_label_links", ["topic_cluster_id"])
    op.create_index("ix_topic_label_links_label_id", "topic_label_links", ["label_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_label_links_label_id", table_name="topic_label_links")
    op.drop_index("ix_topic_label_links_topic_cluster_id", table_name="topic_label_links")
    op.drop_table("topic_label_links")

    op.drop_index("ix_content_candidates_topic_cluster_id", table_name="content_candidates")
    op.drop_index("ix_content_candidates_run_id", table_name="content_candidates")
    op.drop_table("content_candidates")

    op.drop_index("ix_topic_clusters_cluster_hash", table_name="topic_clusters")
    op.drop_index("ix_topic_clusters_run_id", table_name="topic_clusters")
    op.drop_table("topic_clusters")

    op.drop_index("ix_raw_signals_published_at", table_name="raw_signals")
    op.drop_index("ix_raw_signals_source", table_name="raw_signals")
    op.drop_index("ix_raw_signals_run_id", table_name="raw_signals")
    op.drop_table("raw_signals")

    op.drop_index("ix_run_sources_source", table_name="run_sources")
    op.drop_index("ix_run_sources_run_id", table_name="run_sources")
    op.drop_table("run_sources")

    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_profile_id", table_name="runs")
    op.drop_table("runs")

    op.drop_table("labels")
    op.drop_table("profiles")
