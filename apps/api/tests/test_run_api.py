from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Profile
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


def seed_profile(db_session: Session) -> Profile:
    profile = Profile(
        niche=["AI", "automation"],
        icp=["business owners", "CEO", "CTO"],
        regions=["US", "CA", "EU"],
        language="en",
        seeds=["ai agent", "voice ai"],
        negatives=["crypto"],
        settings_json={"content_types": ["linkedin", "x"]},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def test_post_runs_returns_404_when_profile_is_missing() -> None:
    client, _ = make_client()

    response = client.post("/api/runs")

    assert response.status_code == 404


def test_post_runs_creates_pending_run_with_input_snapshot() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        profile = seed_profile(db_session)

    response = client.post("/api/runs")

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["profile_id"] == profile.id
    assert body["status"] == "pending"
    assert body["input_snapshot"]["niche"] == ["AI", "automation"]
    assert body["input_snapshot"]["language"] == "en"
    assert len(body["sources"]) == 5
    assert {source["status"] for source in body["sources"]} == {"pending"}


def test_get_run_by_id_returns_run_status() -> None:
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_profile(db_session)

    created = client.post("/api/runs")
    run_id = created.json()["id"]

    fetched = client.get(f"/api/runs/{run_id}")

    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == run_id
    assert body["status"] == "pending"
    assert len(body["sources"]) == 5


def test_get_run_by_id_returns_404_when_not_found() -> None:
    client, _ = make_client()

    response = client.get("/api/runs/999")

    assert response.status_code == 404
