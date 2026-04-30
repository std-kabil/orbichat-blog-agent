from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from schemas.common import APIModel


class RunCreateResponse(APIModel):
    run_id: UUID
    job_id: str
    run_type: str
    status: str


class RunRead(APIModel):
    id: UUID
    run_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    error_message: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
