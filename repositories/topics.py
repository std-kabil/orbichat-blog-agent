from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Topic
from schemas.common import TopicStatus
from schemas.trend import TopicScoreOutput


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


def select_next_weekly_topic(db: Session) -> Topic | None:
    approved_statement = (
        select(Topic)
        .where(Topic.status == TopicStatus.APPROVED.value)
        .order_by(Topic.created_at.asc())
        .limit(1)
    )
    approved_topic = db.scalars(approved_statement).first()
    if approved_topic is not None:
        return approved_topic

    recommended_statement = (
        select(Topic)
        .where(Topic.recommended.is_(True), Topic.status == TopicStatus.CANDIDATE.value)
        .order_by(Topic.total_score.desc(), Topic.created_at.asc())
        .limit(1)
    )
    return db.scalars(recommended_statement).first()


def mark_topic_drafted(db: Session, topic_id: UUID) -> Topic | None:
    return update_topic_status(db, topic_id, TopicStatus.DRAFTED)


def create_scored_topic(db: Session, *, run_id: UUID, score: TopicScoreOutput) -> Topic:
    topic = Topic(
        run_id=run_id,
        title=score.title,
        target_keyword=score.target_keyword,
        search_intent=score.search_intent,
        summary=None,
        trend_score=score.trend_score,
        orbichat_relevance_score=score.orbichat_relevance_score,
        seo_score=score.seo_score,
        conversion_score=score.conversion_score,
        total_score=score.total_score,
        recommended=score.recommended,
        reasoning=score.reasoning,
        cta_angle=score.cta_angle,
        status=TopicStatus.CANDIDATE.value,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic
