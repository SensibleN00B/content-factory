import logging
from collections.abc import Generator
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Profile, Run, RunSource
from app.infrastructure.db.session import get_db_session
from app.main import create_app
from app.presentation.http.routers import runs as runs_router
from app.presentation.http.routers.runs import get_run_executor


RunExecutor = Callable[[int, sessionmaker[Session]], None]


def make_client(run_executor: RunExecutor | None = None) -> tuple[TestClient, sessionmaker[Session]]:
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

    if run_executor is None:
        def no_op_executor(_: int, __: sessionmaker[Session]) -> None:
            return None

        run_executor = no_op_executor

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_run_executor] = lambda: run_executor

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


def _find_event_record(caplog: object, event_name: str) -> object | None:
    records = getattr(caplog, "records", [])
    for record in records:
        if getattr(record, "event", None) == event_name:
            return record
    return None


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
    assert [source["source"] for source in body["sources"]] == [
        "google_trends",
        "hackernews",
        "producthunt",
        "reddit",
        "youtube",
    ]


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
    assert [source["source"] for source in body["sources"]] == [
        "google_trends",
        "hackernews",
        "producthunt",
        "reddit",
        "youtube",
    ]


def test_post_runs_emits_structured_log_record(caplog: object) -> None:
    caplog.set_level(logging.INFO)
    client, session_factory = make_client()
    with session_factory() as db_session:
        profile = seed_profile(db_session)

    response = client.post("/api/runs")

    assert response.status_code == 201
    body = response.json()
    event_record = _find_event_record(caplog, "run.created")
    assert event_record is not None
    assert getattr(event_record, "run_id", None) == body["id"]
    assert getattr(event_record, "profile_id", None) == profile.id
    assert getattr(event_record, "source_count", None) == 5


def test_post_runs_enqueues_execution_task() -> None:
    called_run_ids: list[int] = []

    def fake_run_executor(run_id: int, _: sessionmaker[Session]) -> None:
        called_run_ids.append(run_id)

    client, session_factory = make_client(run_executor=fake_run_executor)
    with session_factory() as db_session:
        seed_profile(db_session)

    response = client.post("/api/runs")

    assert response.status_code == 201
    body = response.json()
    assert called_run_ids == [body["id"]]


def test_get_run_emits_structured_log_record(caplog: object) -> None:
    caplog.set_level(logging.INFO)
    client, session_factory = make_client()
    with session_factory() as db_session:
        seed_profile(db_session)

    created = client.post("/api/runs")
    run_id = created.json()["id"]
    fetched = client.get(f"/api/runs/{run_id}")

    assert fetched.status_code == 200
    event_record = _find_event_record(caplog, "run.fetched")
    assert event_record is not None
    assert getattr(event_record, "run_id", None) == run_id
    assert getattr(event_record, "status", None) == "pending"
    assert getattr(event_record, "source_failures", None) == 0
    assert getattr(event_record, "candidate_count", None) == 0


def test_execute_run_keeps_duration_ms_nullable_when_pipeline_crashes(monkeypatch: object) -> None:
    _, session_factory = make_client()
    with session_factory() as db_session:
        profile = seed_profile(db_session)
        run = Run(
            profile_id=profile.id,
            status="pending",
            input_snapshot_json={"language": "en", "regions": ["US"], "seeds": ["ai"]},
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        for source_key in ["google_trends", "hackernews", "producthunt", "reddit", "youtube"]:
            db_session.add(
                RunSource(
                    run_id=run.id,
                    source=source_key,
                    status="pending",
                    fetched_count=0,
                    error_text=None,
                    duration_ms=None,
                )
            )
        db_session.commit()

    class _BrokenPipeline:
        def run(self, **_: object) -> object:
            raise RuntimeError("boom")

    monkeypatch.setattr(runs_router, "_build_pipeline", lambda: _BrokenPipeline())

    runs_router._execute_run(run.id, session_factory)

    with session_factory() as verify_session:
        stored_run = verify_session.get(Run, run.id)
        assert stored_run is not None
        assert stored_run.status == "failed"
        source_rows = (
            verify_session.query(RunSource).where(RunSource.run_id == run.id).all()
        )
        assert len(source_rows) == 5
        assert {source.status for source in source_rows} == {"failed"}
        assert all(source.duration_ms is None for source in source_rows)


def test_get_run_by_id_returns_404_when_not_found() -> None:
    client, _ = make_client()

    response = client.get("/api/runs/999")

    assert response.status_code == 404
