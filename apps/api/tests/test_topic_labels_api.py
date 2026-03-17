from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Label, Profile, Run, TopicCluster, TopicLabelLink
from app.infrastructure.db.seeds import ensure_default_labels
from app.infrastructure.db.session import get_db_session
from app.main import create_app


def make_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db_session() -> Generator[Session, None, None]:
        db_session = testing_session_factory()
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    return TestClient(app), testing_session_factory


def seed_topic_cluster(db_session: Session) -> TopicCluster:
    profile = Profile(
        niche=["ai"],
        icp=["ceo"],
        regions=["US"],
        language="en",
        seeds=["ai workflow"],
        negatives=["crypto"],
        settings_json={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    run = Run(
        profile_id=profile.id,
        status="completed",
        input_snapshot_json={"niche": ["ai"], "language": "en"},
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    cluster = TopicCluster(
        run_id=run.id,
        canonical_topic="AI workflow for clinics",
        cluster_hash="cluster-1",
        source_count=2,
        signal_count=3,
        evidence_urls_json=["https://example.com/1"],
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


def test_post_topic_label_creates_link() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        cluster = seed_topic_cluster(db_session)
        ensure_default_labels(db_session)

    response = client.post(f"/api/topics/{cluster.id}/labels", json={"label": "selected_for_post"})

    assert response.status_code == 201
    body = response.json()
    assert body["topic_cluster_id"] == cluster.id
    assert body["label"] == "selected_for_post"
    assert body["created_at"] is not None


def test_post_topic_label_is_idempotent() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        cluster = seed_topic_cluster(db_session)
        ensure_default_labels(db_session)

    first = client.post(f"/api/topics/{cluster.id}/labels", json={"label": "watchlist"})
    second = client.post(f"/api/topics/{cluster.id}/labels", json={"label": "watchlist"})

    assert first.status_code == 201
    assert second.status_code == 200

    with session_factory() as db_session:
        label_id = db_session.scalar(select(Label.id).where(Label.name == "watchlist"))
        links_count = db_session.scalar(
            select(func.count())
            .select_from(TopicLabelLink)
            .where(
                TopicLabelLink.topic_cluster_id == cluster.id,
                TopicLabelLink.label_id == label_id,
            )
        )

    assert links_count == 1


def test_delete_topic_label_removes_link() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        cluster = seed_topic_cluster(db_session)
        labels = ensure_default_labels(db_session)
        selected = next(item for item in labels if item.name == "published")
        link = TopicLabelLink(topic_cluster_id=cluster.id, label_id=selected.id)
        db_session.add(link)
        db_session.commit()

    response = client.delete(f"/api/topics/{cluster.id}/labels/published")

    assert response.status_code == 204

    with session_factory() as db_session:
        label_id = db_session.scalar(select(Label.id).where(Label.name == "published"))
        links_count = db_session.scalar(
            select(func.count())
            .select_from(TopicLabelLink)
            .where(
                TopicLabelLink.topic_cluster_id == cluster.id,
                TopicLabelLink.label_id == label_id,
            )
        )
    assert links_count == 0


def test_post_topic_label_returns_404_for_unknown_topic() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        ensure_default_labels(db_session)

    response = client.post("/api/topics/999/labels", json={"label": "watchlist"})

    assert response.status_code == 404


def test_post_topic_label_returns_404_for_unknown_label() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        cluster = seed_topic_cluster(db_session)
        ensure_default_labels(db_session)

    response = client.post(f"/api/topics/{cluster.id}/labels", json={"label": "unknown_label"})

    assert response.status_code == 404


def test_delete_topic_label_returns_404_when_link_missing() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        cluster = seed_topic_cluster(db_session)
        ensure_default_labels(db_session)

    response = client.delete(f"/api/topics/{cluster.id}/labels/watchlist")

    assert response.status_code == 404
