from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    ContentCandidate,
    Profile,
    Run,
    TopicCluster,
    TopicLabelLink,
)
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


def seed_candidates(db_session: Session) -> tuple[int, int]:
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

    cluster_one = TopicCluster(
        run_id=run.id,
        canonical_topic="AI workflow for clinics",
        cluster_hash="cluster-1",
        source_count=3,
        signal_count=4,
        evidence_urls_json=["https://example.com/1"],
    )
    cluster_two = TopicCluster(
        run_id=run.id,
        canonical_topic="AI outbound automation",
        cluster_hash="cluster-2",
        source_count=2,
        signal_count=2,
        evidence_urls_json=["https://example.com/2"],
    )
    db_session.add_all([cluster_one, cluster_two])
    db_session.commit()
    db_session.refresh(cluster_one)
    db_session.refresh(cluster_two)

    candidate_one = ContentCandidate(
        run_id=run.id,
        topic_cluster_id=cluster_one.id,
        trend_score=85.0,
        score_breakdown_json={"velocity": 90},
        why_now="Strong velocity",
        angles_json=["Angle 1", "Angle 2"],
        confidence=0.8,
    )
    candidate_two = ContentCandidate(
        run_id=run.id,
        topic_cluster_id=cluster_two.id,
        trend_score=72.0,
        score_breakdown_json={"velocity": 70},
        why_now="Steady momentum",
        angles_json=["Angle A", "Angle B"],
        confidence=0.7,
    )
    db_session.add_all([candidate_one, candidate_two])
    db_session.commit()
    db_session.refresh(candidate_one)
    db_session.refresh(candidate_two)

    labels = ensure_default_labels(db_session)
    selected_for_post = next(item for item in labels if item.name == "selected_for_post")
    db_session.add(TopicLabelLink(topic_cluster_id=cluster_one.id, label_id=selected_for_post.id))
    db_session.commit()

    return run.id, cluster_one.id


def test_get_candidates_returns_candidates_sorted_by_score() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        run_id, _ = seed_candidates(db_session)

    response = client.get(f"/api/candidates?run_id={run_id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert [item["trend_score"] for item in body] == [85.0, 72.0]
    assert body[0]["canonical_topic"] == "AI workflow for clinics"


def test_get_candidates_excludes_topics_with_requested_labels() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        run_id, _ = seed_candidates(db_session)

    response = client.get(f"/api/candidates?run_id={run_id}&exclude_labels=selected_for_post")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["canonical_topic"] == "AI outbound automation"
