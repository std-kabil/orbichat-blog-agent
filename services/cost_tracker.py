from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from repositories.call_logs import create_llm_call, create_search_call
from services.pricing import calculate_llm_cost, calculate_search_cost


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0


def monotonic_time() -> float:
    return perf_counter()


def elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def extract_llm_usage(completion: object) -> LLMUsage:
    usage = getattr(completion, "usage", None)
    if usage is None and isinstance(completion, dict):
        usage = completion.get("usage")
    if usage is None:
        return LLMUsage()

    prompt_tokens = _read_int(usage, "prompt_tokens")
    completion_tokens = _read_int(usage, "completion_tokens")
    return LLMUsage(input_tokens=prompt_tokens, output_tokens=completion_tokens)


def record_llm_call(
    db: Session | None,
    *,
    task_name: str,
    model: str,
    latency_ms: int | None,
    settings: Settings | None = None,
    run_id: UUID | None = None,
    draft_id: UUID | None = None,
    topic_id: UUID | None = None,
    usage: LLMUsage | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    if db is None:
        return

    call_usage = usage or LLMUsage()
    estimated_cost_usd = (
        calculate_llm_cost(
            settings=settings,
            model=model,
            input_tokens=call_usage.input_tokens,
            output_tokens=call_usage.output_tokens,
        )
        if settings is not None
        else Decimal("0")
    )
    create_llm_call(
        db,
        task_name=task_name,
        provider="openrouter",
        model=model,
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        input_tokens=call_usage.input_tokens,
        output_tokens=call_usage.output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )


def record_search_call(
    db: Session | None,
    *,
    provider: str,
    query: str,
    result_count: int,
    latency_ms: int | None,
    settings: Settings | None = None,
    run_id: UUID | None = None,
    topic_id: UUID | None = None,
    draft_id: UUID | None = None,
    success: bool = True,
    error: str | None = None,
) -> None:
    if db is None:
        return

    create_search_call(
        db,
        provider=provider,
        query=query,
        run_id=run_id,
        topic_id=topic_id,
        draft_id=draft_id,
        result_count=result_count,
        estimated_cost_usd=(
            calculate_search_cost(settings=settings, provider=provider)
            if settings is not None
            else Decimal("0")
        ),
        latency_ms=latency_ms,
        success=success,
        error=error,
    )


def _read_int(container: object, key: str) -> int:
    value: object
    if isinstance(container, dict):
        value = container.get(key, 0)
    else:
        value = getattr(container, key, 0)

    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int(str(value))
