from datetime import datetime
from uuid import UUID

from schemas.common import APIModel, TopicStatus


class TopicRead(APIModel):
    id: UUID
    run_id: UUID | None
    title: str
    target_keyword: str | None
    search_intent: str | None
    summary: str | None
    trend_score: int
    orbichat_relevance_score: int
    seo_score: int
    conversion_score: int
    total_score: int
    recommended: bool
    reasoning: str | None
    cta_angle: str | None
    status: TopicStatus
    created_at: datetime
    updated_at: datetime
