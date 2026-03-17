from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Label

DEFAULT_LABELS: list[tuple[str, str]] = [
    ("selected_for_post", "Topic selected for upcoming content production"),
    ("published", "Topic already published and should be excluded from fresh picks"),
    ("not_relevant", "Topic does not match current business focus"),
    ("duplicate", "Topic duplicates existing idea and should be hidden"),
    ("watchlist", "Topic is promising and should be monitored"),
]


def ensure_default_labels(db_session: Session) -> list[Label]:
    label_names = [name for name, _ in DEFAULT_LABELS]
    existing_labels = db_session.scalars(select(Label).where(Label.name.in_(label_names))).all()
    existing_by_name = {label.name: label for label in existing_labels}

    created = False
    for name, description in DEFAULT_LABELS:
        if name in existing_by_name:
            continue
        db_session.add(Label(name=name, description=description))
        created = True

    if created:
        db_session.commit()

    final_labels = db_session.scalars(select(Label).where(Label.name.in_(label_names))).all()
    final_by_name = {label.name: label for label in final_labels}
    return [final_by_name[name] for name in label_names if name in final_by_name]
