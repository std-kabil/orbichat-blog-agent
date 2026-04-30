from datetime import datetime
from decimal import Decimal
from uuid import UUID

from schemas.common import APIModel


class LLMCallRead(APIModel):
    id: UUID
    run_id: UUID | None
    draft_id: UUID | None
    topic_id: UUID | None
    task_name: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    latency_ms: int | None
    success: bool
    error: str | None
    created_at: datetime


class SearchCallRead(APIModel):
    id: UUID
    run_id: UUID | None
    topic_id: UUID | None
    draft_id: UUID | None
    provider: str
    query: str
    result_count: int
    estimated_cost_usd: Decimal
    latency_ms: int | None
    success: bool
    error: str | None
    created_at: datetime
