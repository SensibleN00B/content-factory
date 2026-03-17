from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Label
from app.infrastructure.db.seeds import ensure_default_labels
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.label import LabelOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api", tags=["labels"])


def _to_label_out(label: Label) -> LabelOut:
    return LabelOut(
        id=label.id,
        name=label.name,
        description=label.description,
        created_at=label.created_at,
    )


@router.get("/labels", response_model=list[LabelOut])
def get_labels(db_session: DbSession) -> list[LabelOut]:
    labels = ensure_default_labels(db_session)
    return [_to_label_out(label) for label in labels]
