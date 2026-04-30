from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LLMCall, SearchCall
from schemas.cost import CostSummary, ModelUsageSummary


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int(str(value))


def summarize_costs(db: Session, run_id: UUID | None = None) -> CostSummary:
    llm_totals_statement = select(
        func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0),
        func.coalesce(func.sum(LLMCall.input_tokens), 0),
        func.coalesce(func.sum(LLMCall.output_tokens), 0),
        func.count(LLMCall.id),
    )
    if run_id is not None:
        llm_totals_statement = llm_totals_statement.where(LLMCall.run_id == run_id)
    llm_cost, input_tokens, output_tokens, llm_count = db.execute(llm_totals_statement).one()

    search_totals_statement = select(
        func.coalesce(func.sum(SearchCall.estimated_cost_usd), 0),
        func.count(SearchCall.id),
    )
    if run_id is not None:
        search_totals_statement = search_totals_statement.where(SearchCall.run_id == run_id)
    search_cost, search_count = db.execute(search_totals_statement).one()

    usage_statement = select(
        LLMCall.provider,
        LLMCall.model,
        func.count(LLMCall.id),
        func.coalesce(func.sum(LLMCall.input_tokens), 0),
        func.coalesce(func.sum(LLMCall.output_tokens), 0),
        func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0),
    ).group_by(LLMCall.provider, LLMCall.model)
    if run_id is not None:
        usage_statement = usage_statement.where(LLMCall.run_id == run_id)

    model_usage = [
        ModelUsageSummary(
            provider=str(provider),
            model=str(model),
            call_count=_int(call_count),
            input_tokens=_int(model_input_tokens),
            output_tokens=_int(model_output_tokens),
            estimated_cost_usd=_decimal(model_cost),
        )
        for (
            provider,
            model,
            call_count,
            model_input_tokens,
            model_output_tokens,
            model_cost,
        ) in db.execute(usage_statement).all()
    ]

    return CostSummary(
        run_id=run_id,
        total_estimated_cost_usd=_decimal(llm_cost) + _decimal(search_cost),
        total_input_tokens=_int(input_tokens),
        total_output_tokens=_int(output_tokens),
        llm_call_count=_int(llm_count),
        search_call_count=_int(search_count),
        model_usage=model_usage,
    )
