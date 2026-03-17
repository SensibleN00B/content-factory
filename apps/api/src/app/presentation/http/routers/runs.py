from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Profile, Run
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.run import RunOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api", tags=["runs"])


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


def _to_run_out(run: Run) -> RunOut:
    return RunOut(
        id=run.id,
        profile_id=run.profile_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_snapshot=run.input_snapshot_json,
        error_summary=run.error_summary,
        created_at=run.created_at,
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

    return _to_run_out(run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db_session: DbSession) -> RunOut:
    run = db_session.get(Run, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return _to_run_out(run)
