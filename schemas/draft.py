from datetime import datetime
from typing import Any
from uuid import UUID

from schemas.common import APIModel, DraftStatus
from schemas.workflow import DraftFeedbackOutput


class DraftRead(APIModel):
    id: UUID
    topic_id: UUID
    title: str
    slug: str
    meta_title: str | None
    meta_description: str | None
    target_keyword: str | None
    markdown_content: str
    outline_json: dict[str, Any]
    seo_json: dict[str, Any]
    status: DraftStatus
    version: int
    publish_score: int | None
    publish_ready: bool
    payload_post_id: str | None
    created_at: datetime
    updated_at: datetime


class DraftFeedbackRead(APIModel):
    draft_id: UUID
    feedback: DraftFeedbackOutput | None
    model: str | None = None
    created_from_draft_id: UUID | None = None
    additional_instructions: str | None = None
