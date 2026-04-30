from datetime import datetime
from uuid import UUID

from schemas.common import APIModel


class FactCheckRead(APIModel):
    id: UUID
    draft_id: UUID
    claim: str
    claim_type: str | None
    verdict: str
    severity: str
    explanation: str | None
    source_urls_json: list[str]
    recommended_action: str | None
    created_at: datetime
