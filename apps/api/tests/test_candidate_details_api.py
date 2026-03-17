from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import ContentCandidate, Profile, Run, TopicCluster
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


def seed_candidate(db_session: Session) -> int:
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
        source_count=3,
        signal_count=4,
        evidence_urls_json=["https://example.com/1", "https://example.com/2"],
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)

    candidate = ContentCandidate(
        run_id=run.id,
        topic_cluster_id=cluster.id,
        trend_score=88.5,
        score_breakdown_json={
            "velocity": 91.2,
            "volume": 77.8,
            "engagement": 81.4,
            "relevance": 95.0,
            "opinionability": 61.0,
        },
        why_now="Strong velocity and relevance signal now",
        angles_json=["Angle 1", "Angle 2", "Angle 3"],
        confidence=0.84,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    return candidate.id


def test_get_candidate_details_returns_evidence_and_angles() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        candidate_id = seed_candidate(db_session)

    response = client.get(f"/api/candidates/{candidate_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == candidate_id
    assert body["canonical_topic"] == "AI workflow for clinics"
    assert body["evidence_urls"] == ["https://example.com/1", "https://example.com/2"]
    assert body["angles"] == ["Angle 1", "Angle 2", "Angle 3"]
    assert "velocity" in body["score_breakdown"]


def test_get_candidate_details_returns_404_for_unknown_id() -> None:
    client, _ = make_client()

    response = client.get("/api/candidates/999")

    assert response.status_code == 404
