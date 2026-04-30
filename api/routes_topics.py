from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from agents.orchestrator import run_weekly_blog_generation
from app.config import get_settings
from app.dependencies import get_database_session
from app.errors import not_found
from repositories.runs import create_run
from repositories.topics import get_topic, list_topics as list_topics_repo, update_topic_status
from schemas.common import RunType, TopicStatus
from schemas.topic import TopicRead
from schemas.workflow import WeeklyBlogGenerationResult

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicRead])
def list_topics(
    db: Session = Depends(get_database_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TopicRead]:
    topics = list_topics_repo(db, limit=limit)
    return [TopicRead.model_validate(topic) for topic in topics]


@router.get("/{topic_id}", response_model=TopicRead)
def read_topic(
    topic_id: UUID,
    db: Session = Depends(get_database_session),
) -> TopicRead:
    topic = get_topic(db, topic_id)
    if topic is None:
        raise not_found("Topic not found")
    return TopicRead.model_validate(topic)


@router.post("/{topic_id}/approve", response_model=TopicRead)
def approve_topic(
    topic_id: UUID,
    db: Session = Depends(get_database_session),
) -> TopicRead:
    topic = update_topic_status(db, topic_id, TopicStatus.APPROVED)
    if topic is None:
        raise not_found("Topic not found")
    return TopicRead.model_validate(topic)


@router.post("/{topic_id}/reject", response_model=TopicRead)
def reject_topic(
    topic_id: UUID,
    db: Session = Depends(get_database_session),
) -> TopicRead:
    topic = update_topic_status(db, topic_id, TopicStatus.REJECTED)
    if topic is None:
        raise not_found("Topic not found")
    return TopicRead.model_validate(topic)


@router.post("/{topic_id}/generate-draft", response_model=WeeklyBlogGenerationResult)
async def generate_topic_draft(
    topic_id: UUID,
    db: Session = Depends(get_database_session),
) -> WeeklyBlogGenerationResult:
    topic = get_topic(db, topic_id)
    if topic is None:
        raise not_found("Topic not found")

    run = create_run(db, RunType.MANUAL_DRAFT)
    return await run_weekly_blog_generation(
        settings=get_settings(),
        db=db,
        run_id=run.id,
        topic_id=topic_id,
    )
