from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Label, TopicCluster, TopicLabelLink
from app.infrastructure.db.seeds import ensure_default_labels
from app.infrastructure.db.session import get_db_session
from app.presentation.http.schemas.topic_label import TopicLabelAssignIn, TopicLabelOut

DbSession = Annotated[Session, Depends(get_db_session)]

router = APIRouter(prefix="/api/topics", tags=["topic-labels"])


def _to_topic_label_out(*, link: TopicLabelLink, label: Label) -> TopicLabelOut:
    return TopicLabelOut(
        topic_cluster_id=link.topic_cluster_id,
        label=label.name,
        created_at=link.created_at,
    )


@router.post(
    "/{topic_cluster_id}/labels",
    response_model=TopicLabelOut,
    status_code=status.HTTP_201_CREATED,
)
def add_topic_label(
    topic_cluster_id: int,
    payload: TopicLabelAssignIn,
    response: Response,
    db_session: DbSession,
) -> TopicLabelOut:
    topic_cluster = db_session.get(TopicCluster, topic_cluster_id)
    if topic_cluster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic cluster not found")

    ensure_default_labels(db_session)
    label_name = payload.label.strip()
    label = db_session.scalar(select(Label).where(Label.name == label_name))
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")

    existing_link = db_session.scalar(
        select(TopicLabelLink).where(
            TopicLabelLink.topic_cluster_id == topic_cluster_id,
            TopicLabelLink.label_id == label.id,
        )
    )
    if existing_link is not None:
        response.status_code = status.HTTP_200_OK
        return _to_topic_label_out(link=existing_link, label=label)

    link = TopicLabelLink(topic_cluster_id=topic_cluster_id, label_id=label.id)
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return _to_topic_label_out(link=link, label=label)


@router.delete(
    "/{topic_cluster_id}/labels/{label_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_topic_label(topic_cluster_id: int, label_name: str, db_session: DbSession) -> Response:
    topic_cluster = db_session.get(TopicCluster, topic_cluster_id)
    if topic_cluster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic cluster not found")

    label = db_session.scalar(select(Label).where(Label.name == label_name.strip()))
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")

    link = db_session.scalar(
        select(TopicLabelLink).where(
            TopicLabelLink.topic_cluster_id == topic_cluster_id,
            TopicLabelLink.label_id == label.id,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic label not found")

    db_session.delete(link)
    db_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
