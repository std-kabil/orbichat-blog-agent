from datetime import datetime
from typing import Any
from uuid import UUID

from schemas.common import APIModel


class SocialPostRead(APIModel):
    id: UUID
    draft_id: UUID
    platform: str
    content: str
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
