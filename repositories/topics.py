from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Topic
from schemas.common import TopicStatus


def list_topics(db: Session, limit: int = 50) -> list[Topic]:
    statement = select(Topic).order_by(Topic.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_topic(db: Session, topic_id: UUID) -> Topic | None:
    return db.get(Topic, topic_id)


def update_topic_status(db: Session, topic_id: UUID, status: TopicStatus) -> Topic | None:
    topic = get_topic(db, topic_id)
    if topic is None:
        return None

    topic.status = status.value
    db.commit()
    db.refresh(topic)
    return topic
