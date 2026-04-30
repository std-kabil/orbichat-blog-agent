from datetime import datetime
from typing import Any
from uuid import UUID

from schemas.common import APIModel


class SourceRead(APIModel):
    id: UUID
    topic_id: UUID | None
    draft_id: UUID | None
    url: str
    title: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    extracted_text: str | None
    snippet: str | None
    credibility_score: int | None
    source_type: str | None
    used_in_article: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
