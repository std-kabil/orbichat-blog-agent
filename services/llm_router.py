import json
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from services.budget import assert_budget_available
from services.cost_tracker import elapsed_ms, extract_llm_usage, monotonic_time, record_llm_call
from services.errors import ProviderResponseError
from services.openrouter_client import ChatMessage, OpenRouterClient, extract_message_content
from services.pricing import estimate_llm_call_cost

OutputModel = TypeVar("OutputModel", bound=BaseModel)


async def call_openrouter_text(
    *,
    settings: Settings,
    model: str,
    messages: list[ChatMessage],
    task_name: str,
    db: Session | None = None,
    run_id: UUID | None = None,
    draft_id: UUID | None = None,
    topic_id: UUID | None = None,
    client: OpenRouterClient | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    started_at = monotonic_time()
    try:
        assert_budget_available(
            settings=settings,
            db=db,
            estimated_cost_usd=estimate_llm_call_cost(
                settings=settings,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            ),
            run_id=run_id,
            task_name=task_name,
            provider="openrouter",
            model=model,
        )
        openrouter = client or OpenRouterClient(settings)
        completion = await openrouter.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = elapsed_ms(started_at)
        content = extract_message_content(completion)
        record_llm_call(
            db,
            task_name=task_name,
            model=model,
            settings=settings,
            run_id=run_id,
            draft_id=draft_id,
            topic_id=topic_id,
            latency_ms=latency_ms,
            usage=extract_llm_usage(completion),
            success=True,
        )
        return content
    except Exception as exc:
        record_llm_call(
            db,
            task_name=task_name,
            model=model,
            settings=settings,
            run_id=run_id,
            draft_id=draft_id,
            topic_id=topic_id,
            latency_ms=elapsed_ms(started_at),
            success=False,
            error=str(exc),
        )
        raise


async def call_openrouter_json(
    *,
    settings: Settings,
    model: str,
    messages: list[ChatMessage],
    task_name: str,
    response_model: type[OutputModel],
    db: Session | None = None,
    run_id: UUID | None = None,
    draft_id: UUID | None = None,
    topic_id: UUID | None = None,
    client: OpenRouterClient | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> OutputModel:
    started_at = monotonic_time()
    response_format: dict[str, object] = {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "strict": True,
            "schema": response_model.model_json_schema(),
        },
    }
    try:
        assert_budget_available(
            settings=settings,
            db=db,
            estimated_cost_usd=estimate_llm_call_cost(
                settings=settings,
                model=model,
                messages=messages,
                max_tokens=max_tokens,
            ),
            run_id=run_id,
            task_name=task_name,
            provider="openrouter",
            model=model,
        )
        openrouter = client or OpenRouterClient(settings)
        completion = await openrouter.chat_completion(
            model=model,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = elapsed_ms(started_at)
        parsed = _parse_json_content(extract_message_content(completion), response_model)
        record_llm_call(
            db,
            task_name=task_name,
            model=model,
            settings=settings,
            run_id=run_id,
            draft_id=draft_id,
            topic_id=topic_id,
            latency_ms=latency_ms,
            usage=extract_llm_usage(completion),
            success=True,
        )
        return parsed
    except Exception as exc:
        record_llm_call(
            db,
            task_name=task_name,
            model=model,
            settings=settings,
            run_id=run_id,
            draft_id=draft_id,
            topic_id=topic_id,
            latency_ms=elapsed_ms(started_at),
            success=False,
            error=str(exc),
        )
        raise


def _parse_json_content(content: str, response_model: type[OutputModel]) -> OutputModel:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("OpenRouter response content was not valid JSON") from exc

    try:
        return response_model.model_validate(payload)
    except ValidationError:
        raise
