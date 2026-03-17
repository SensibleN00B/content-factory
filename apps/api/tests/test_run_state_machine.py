from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Profile, Run


def make_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


def seed_profile(db_session: Session) -> Profile:
    profile = Profile(
        niche=["AI", "automation"],
        icp=["business owners", "CEO", "CTO"],
        regions=["US", "CA", "EU"],
        language="en",
        seeds=["ai agent"],
        negatives=["crypto"],
        settings_json={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def seed_run(db_session: Session, profile_id: int, status: str = "pending") -> Run:
    run = Run(
        profile_id=profile_id,
        status=status,
        input_snapshot_json={"niche": ["AI"]},
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_transition_happy_path_updates_timestamps() -> None:
    from app.domain.runs.state_machine import RunStateMachine

    session_factory = make_session_factory()

    with session_factory() as db_session:
        profile = seed_profile(db_session)
        run = seed_run(db_session, profile.id, status="pending")

        machine = RunStateMachine()
        now = datetime.now(UTC)

        run = machine.transition(
            db_session=db_session,
            run=run,
            target_status="collecting",
            now=now,
        )
        assert run.status == "collecting"
        assert run.started_at is not None
        assert run.finished_at is None

        run = machine.transition(db_session=db_session, run=run, target_status="processing")
        assert run.status == "processing"

        run = machine.transition(db_session=db_session, run=run, target_status="scoring")
        assert run.status == "scoring"

        run = machine.transition(db_session=db_session, run=run, target_status="completed")
        assert run.status == "completed"
        assert run.finished_at is not None


def test_transition_to_failed_is_allowed_from_collecting() -> None:
    from app.domain.runs.state_machine import RunStateMachine

    session_factory = make_session_factory()

    with session_factory() as db_session:
        profile = seed_profile(db_session)
        run = seed_run(db_session, profile.id, status="collecting")

        machine = RunStateMachine()
        run = machine.transition(
            db_session=db_session,
            run=run,
            target_status="failed",
            error_summary="collector timeout",
        )

        assert run.status == "failed"
        assert run.error_summary == "collector timeout"
        assert run.finished_at is not None


def test_invalid_transition_is_rejected() -> None:
    from app.domain.runs.state_machine import InvalidRunTransitionError, RunStateMachine

    session_factory = make_session_factory()

    with session_factory() as db_session:
        profile = seed_profile(db_session)
        run = seed_run(db_session, profile.id, status="pending")

        machine = RunStateMachine()
        with pytest.raises(InvalidRunTransitionError):
            machine.transition(db_session=db_session, run=run, target_status="processing")


def test_terminal_state_transition_is_rejected() -> None:
    from app.domain.runs.state_machine import InvalidRunTransitionError, RunStateMachine

    session_factory = make_session_factory()

    with session_factory() as db_session:
        profile = seed_profile(db_session)
        run = seed_run(db_session, profile.id, status="completed")

        machine = RunStateMachine()
        with pytest.raises(InvalidRunTransitionError):
            machine.transition(db_session=db_session, run=run, target_status="collecting")
