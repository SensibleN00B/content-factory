from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Profile
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.profile import ProfileIn, ProfileOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api", tags=["profile"])


def _to_profile_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        niche=profile.niche or [],
        icp=profile.icp or [],
        regions=profile.regions or [],
        language=profile.language,
        seeds=profile.seeds or [],
        negatives=profile.negatives or [],
        settings=profile.settings_json or {},
        created_at=profile.created_at,
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(db_session: DbSession) -> ProfileOut:
    profile = db_session.scalar(select(Profile).order_by(Profile.id.asc()).limit(1))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile is not initialized",
        )

    return _to_profile_out(profile)


@router.put("/profile", response_model=ProfileOut)
def upsert_profile(payload: ProfileIn, db_session: DbSession) -> ProfileOut:
    profile = db_session.scalar(select(Profile).order_by(Profile.id.asc()).limit(1))

    if profile is None:
        profile = Profile(
            niche=payload.niche,
            icp=payload.icp,
            regions=payload.regions,
            language=payload.language,
            seeds=payload.seeds,
            negatives=payload.negatives,
            settings_json=payload.settings,
        )
        db_session.add(profile)
    else:
        profile.niche = payload.niche
        profile.icp = payload.icp
        profile.regions = payload.regions
        profile.language = payload.language
        profile.seeds = payload.seeds
        profile.negatives = payload.negatives
        profile.settings_json = payload.settings

    db_session.commit()
    db_session.refresh(profile)

    return _to_profile_out(profile)
