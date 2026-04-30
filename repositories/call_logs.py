from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import LLMCall, SearchCall


def create_llm_call(
    db: Session,
    *,
    task_name: str,
    provider: str,
    model: str,
    run_id: UUID | None = None,
    draft_id: UUID | None = None,
    topic_id: UUID | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    estimated_cost_usd: Decimal = Decimal("0"),
    latency_ms: int | None = None,
    success: bool = True,
    error: str | None = None,
) -> LLMCall:
    call = LLMCall(
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        task_name=task_name,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def create_search_call(
    db: Session,
    *,
    provider: str,
    query: str,
    run_id: UUID | None = None,
    topic_id: UUID | None = None,
    draft_id: UUID | None = None,
    result_count: int = 0,
    estimated_cost_usd: Decimal = Decimal("0"),
    latency_ms: int | None = None,
    success: bool = True,
    error: str | None = None,
) -> SearchCall:
    call = SearchCall(
        run_id=run_id,
        topic_id=topic_id,
        draft_id=draft_id,
        provider=provider,
        query=query,
        result_count=result_count,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call
