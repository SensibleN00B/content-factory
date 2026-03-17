from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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


def test_get_profile_returns_404_when_not_initialized() -> None:
    client, _ = make_client()

    response = client.get("/api/profile")

    assert response.status_code == 404


def test_put_profile_creates_profile() -> None:
    client, _ = make_client()

    payload = {
        "niche": ["AI", "automation"],
        "icp": ["business owners", "CEO"],
        "regions": ["US", "CA", "EU"],
        "language": "en",
        "seeds": ["ai agent", "voice ai"],
        "negatives": ["crypto"],
        "settings": {"content_types": ["linkedin", "x"]},
    }

    response = client.put("/api/profile", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["niche"] == payload["niche"]
    assert body["language"] == "en"


def test_put_profile_updates_existing_profile_not_creates_duplicate() -> None:
    client, session_factory = make_client()

    first_payload = {
        "niche": ["AI"],
        "icp": ["CTO"],
        "regions": ["US"],
        "language": "en",
        "seeds": ["agent"],
        "negatives": ["politics"],
        "settings": {"mode": "strict"},
    }
    second_payload = {
        "niche": ["automation"],
        "icp": ["CEO"],
        "regions": ["EU"],
        "language": "en",
        "seeds": ["workflow"],
        "negatives": ["gaming"],
        "settings": {"mode": "soft"},
    }

    created = client.put("/api/profile", json=first_payload)
    updated = client.put("/api/profile", json=second_payload)

    assert created.status_code == 200
    assert updated.status_code == 200
    assert created.json()["id"] == updated.json()["id"]
    assert updated.json()["niche"] == second_payload["niche"]

    with session_factory() as db_session:
        profile_count = db_session.scalar(select(func.count()).select_from(Profile))

    assert profile_count == 1
