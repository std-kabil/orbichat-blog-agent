from decimal import Decimal
from uuid import UUID

from schemas.common import APIModel


class ModelUsageSummary(APIModel):
    provider: str
    model: str
    call_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal


class CostSummary(APIModel):
    run_id: UUID | None
    total_estimated_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    llm_call_count: int
    search_call_count: int
    model_usage: list[ModelUsageSummary]
