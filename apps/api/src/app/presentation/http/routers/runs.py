from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.observability import log_event
from app.infrastructure.db.models import ContentCandidate, Profile, Run, RunSource
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.run import RunOut, RunSourceOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api", tags=["runs"])
MVP_SOURCE_KEYS = ["google_trends", "reddit", "hackernews", "producthunt", "youtube"]
logger = logging.getLogger(__name__)


def _profile_snapshot(profile: Profile) -> dict[str, Any]:
    return {
        "niche": profile.niche or [],
        "icp": profile.icp or [],
        "regions": profile.regions or [],
        "language": profile.language,
        "seeds": profile.seeds or [],
        "negatives": profile.negatives or [],
        "settings": profile.settings_json or {},
    }


def _to_run_out(run: Run, *, sources: list[RunSource]) -> RunOut:
    return RunOut(
        id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_snapshot=run.input_snapshot_json,
        error_summary=run.error_summary,
        created_at=run.created_at,
        sources=[
            RunSourceOut(
                source=source.source,
                status=source.status,
                fetched_count=source.fetched_count,
                error_text=source.error_text,
                duration_ms=source.duration_ms,
                created_at=source.created_at,
            )
            for source in sources
        ],
    )


def _fetch_run_sources(db_session: Session, *, run_id: int) -> list[RunSource]:
    return list(
        db_session.scalars(
            select(RunSource).where(RunSource.run_id == run_id).order_by(RunSource.source.asc())
        )
    )


@router.post("/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(db_session: DbSession) -> RunOut:
    profile = db_session.scalar(select(Profile).order_by(Profile.id.asc()).limit(1))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile is not initialized",
        )

    run = Run(
        profile_id=profile.id,
        status="pending",
        input_snapshot_json=_profile_snapshot(profile),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    for source_key in MVP_SOURCE_KEYS:
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
    run_sources = _fetch_run_sources(db_session, run_id=run.id)

    log_event(
        logger,
        logging.INFO,
        "run.created",
        run_id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        source_count=len(run_sources),
    )

    return _to_run_out(run, sources=run_sources)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db_session: DbSession) -> RunOut:
    run = db_session.get(Run, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    run_sources = _fetch_run_sources(db_session, run_id=run_id)
    candidate_count = (
        db_session.scalar(
            select(func.count(ContentCandidate.id)).where(ContentCandidate.run_id == run_id)
        )
        or 0
    )
    source_failures = sum(
        1 for source in run_sources if source.status.lower() in {"failed", "timeout"}
    )
    run_duration_ms: int | None = None
    if run.started_at is not None and run.finished_at is not None:
        run_duration_ms = max(0, int((run.finished_at - run.started_at).total_seconds() * 1000))

    log_event(
        logger,
        logging.INFO,
        "run.fetched",
        run_id=run.id,
        status=run.status,
        source_failures=source_failures,
        candidate_count=int(candidate_count),
        duration_ms=run_duration_ms,
    )

    return _to_run_out(run, sources=run_sources)
