from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import LLMCall, SearchCall
from services.errors import BudgetExceededError


def assert_budget_available(
    *,
    settings: Settings,
    db: Session | None,
    estimated_cost_usd: Decimal,
    run_id: UUID | None = None,
    task_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    if db is None or estimated_cost_usd <= 0:
        return

    now = datetime.now(UTC)
    daily_spend = _spend_since(db, datetime(now.year, now.month, now.day, tzinfo=UTC))
    monthly_spend = _spend_since(db, datetime(now.year, now.month, 1, tzinfo=UTC))
    daily_projected = daily_spend + estimated_cost_usd
    monthly_projected = monthly_spend + estimated_cost_usd

    if daily_projected > settings.agent_daily_budget_usd:
        _raise_budget_error(
            budget_name="daily",
            limit=settings.agent_daily_budget_usd,
            current=daily_spend,
            estimated=estimated_cost_usd,
            run_id=run_id,
            task_name=task_name,
            provider=provider,
            model=model,
        )

    if monthly_projected > settings.agent_monthly_budget_usd:
        _raise_budget_error(
            budget_name="monthly",
            limit=settings.agent_monthly_budget_usd,
            current=monthly_spend,
            estimated=estimated_cost_usd,
            run_id=run_id,
            task_name=task_name,
            provider=provider,
            model=model,
        )


def _spend_since(db: Session, since: datetime) -> Decimal:
    llm_total = db.execute(
        select(func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0)).where(LLMCall.created_at >= since)
    ).scalar_one()
    search_total = db.execute(
        select(func.coalesce(func.sum(SearchCall.estimated_cost_usd), 0)).where(
            SearchCall.created_at >= since
        )
    ).scalar_one()
    return _decimal(llm_total) + _decimal(search_total)


def _raise_budget_error(
    *,
    budget_name: str,
    limit: Decimal,
    current: Decimal,
    estimated: Decimal,
    run_id: UUID | None,
    task_name: str | None,
    provider: str | None,
    model: str | None,
) -> None:
    message = (
        f"{budget_name.capitalize()} budget exceeded: current ${current}, "
        f"estimated call ${estimated}, limit ${limit}"
    )
    logger.bind(
        run_id=str(run_id) if run_id else None,
        task_name=task_name,
        provider=provider,
        model=model,
        status="budget_blocked",
    ).warning(message)
    raise BudgetExceededError(message)


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
