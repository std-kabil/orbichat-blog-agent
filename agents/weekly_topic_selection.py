from sqlalchemy.orm import Session

from app.models import Topic
from repositories.topics import select_next_weekly_topic


def select_topic_for_weekly_draft(db: Session) -> Topic:
    topic = select_next_weekly_topic(db)
    if topic is None:
        raise RuntimeError("No approved or recommended topic is available for weekly draft generation")
    return topic
