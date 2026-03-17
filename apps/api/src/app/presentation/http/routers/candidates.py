from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import ContentCandidate, Label, TopicCluster, TopicLabelLink
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.candidate import CandidateOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api", tags=["candidates"])


@router.get("/candidates", response_model=list[CandidateOut])
def get_candidates(
    db_session: DbSession,
    run_id: int | None = None,
    exclude_labels: Annotated[list[str] | None, Query()] = None,
) -> list[CandidateOut]:
    statement = select(ContentCandidate, TopicCluster).join(
        TopicCluster,
        TopicCluster.id == ContentCandidate.topic_cluster_id,
    )
    if run_id is not None:
        statement = statement.where(ContentCandidate.run_id == run_id)
    statement = statement.order_by(ContentCandidate.trend_score.desc(), ContentCandidate.id.asc())

    rows = db_session.execute(statement).all()
    if not rows:
        return []

    topic_cluster_ids = [topic_cluster.id for _, topic_cluster in rows]
    labels_map = _load_topic_labels(
        db_session=db_session,
        topic_cluster_ids=topic_cluster_ids,
    )
    excluded_labels_set = {
        value.strip().lower() for value in (exclude_labels or []) if value.strip()
    }

    result: list[CandidateOut] = []
    for candidate, topic_cluster in rows:
        labels = labels_map.get(topic_cluster.id, [])
        if excluded_labels_set and any(label.lower() in excluded_labels_set for label in labels):
            continue

        result.append(
            CandidateOut(
                id=candidate.id,
                run_id=candidate.run_id,
                topic_cluster_id=topic_cluster.id,
                canonical_topic=topic_cluster.canonical_topic,
                trend_score=round(candidate.trend_score, 2),
                why_now=candidate.why_now,
                labels=labels,
                created_at=candidate.created_at,
            )
        )

    return result


def _load_topic_labels(
    *,
    db_session: Session,
    topic_cluster_ids: list[int],
) -> dict[int, list[str]]:
    if not topic_cluster_ids:
        return {}

    statement = (
        select(TopicLabelLink.topic_cluster_id, Label.name)
        .join(Label, Label.id == TopicLabelLink.label_id)
        .where(TopicLabelLink.topic_cluster_id.in_(topic_cluster_ids))
    )
    rows = db_session.execute(statement).all()

    labels_map: dict[int, list[str]] = {}
    for topic_cluster_id, label_name in rows:
        labels_map.setdefault(topic_cluster_id, []).append(label_name)

    for topic_cluster_id in labels_map:
        labels_map[topic_cluster_id] = sorted(set(labels_map[topic_cluster_id]))

    return labels_map
