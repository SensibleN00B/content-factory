from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base

EXPECTED_TABLES = {
    "profiles",
    "runs",
    "run_sources",
    "raw_signals",
    "topic_clusters",
    "content_candidates",
    "labels",
    "topic_label_links",
}


def test_expected_core_tables_are_registered_in_metadata() -> None:
    actual_tables = set(Base.metadata.tables.keys())

    assert EXPECTED_TABLES.issubset(actual_tables)


def test_topic_label_links_has_unique_constraint_for_topic_and_label() -> None:
    table = Base.metadata.tables["topic_label_links"]

    unique_constraints = {
        tuple(sorted(column.name for column in constraint.columns))
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("label_id", "topic_cluster_id") in unique_constraints


def test_runs_table_has_foreign_key_to_profiles() -> None:
    runs_table = Base.metadata.tables["runs"]
    profile_fk = next(iter(runs_table.columns["profile_id"].foreign_keys))

    assert profile_fk.target_fullname == "profiles.id"
