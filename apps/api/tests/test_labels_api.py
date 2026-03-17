from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Label
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


def test_get_labels_returns_seeded_dictionary() -> None:
    client, _ = make_client()

    response = client.get("/api/labels")

    assert response.status_code == 200
    body = response.json()
    names = [item["name"] for item in body]
    assert names == [
        "selected_for_post",
        "published",
        "not_relevant",
        "duplicate",
        "watchlist",
    ]


def test_get_labels_is_idempotent_and_does_not_create_duplicates() -> None:
    client, session_factory = make_client()

    first = client.get("/api/labels")
    second = client.get("/api/labels")

    assert first.status_code == 200
    assert second.status_code == 200

    with session_factory() as db_session:
        label_count = db_session.scalar(select(func.count()).select_from(Label))

    assert label_count == 5
