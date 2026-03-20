from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.dashboard import DashboardBriefingOut
from app.services.dashboard_briefing import build_dashboard_briefing

router = APIRouter(prefix="/api", tags=["dashboard"])

DbSession = Annotated[Session, Depends(get_db_session)]


@router.get("/dashboard/briefing", response_model=DashboardBriefingOut)
def get_dashboard_briefing(db_session: DbSession) -> DashboardBriefingOut:
    return build_dashboard_briefing(db_session=db_session)
