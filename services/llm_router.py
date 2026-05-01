import json
import re
from typing import TypeVar, get_origin
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from services.budget import assert_budget_available
from services.cost_tracker import elapsed_ms, extract_llm_usage, monotonic_time, record_llm_call
from services.errors import ProviderResponseError
from services.openrouter_client import ChatMessage, OpenRouterClient, extract_message_content
from services.pricing import estimate_llm_call_cost
from services.prompts import render_prompt

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
    max_attempts: int = 2,
) -> OutputModel:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    schema_dict = response_model.model_json_schema()
    response_format: dict[str, object] = {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "strict": True,
            "schema": schema_dict,
        },
    }
    openrouter = client or OpenRouterClient(settings)
    base_messages = _prepend_schema_instruction(messages, response_model.__name__, schema_dict)
    attempt_messages: list[ChatMessage] = list(base_messages)

    parse_failure: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        started_at = monotonic_time()
        try:
            assert_budget_available(
                settings=settings,
                db=db,
                estimated_cost_usd=estimate_llm_call_cost(
                    settings=settings,
                    model=model,
                    messages=attempt_messages,
                    max_tokens=max_tokens,
                ),
                run_id=run_id,
                task_name=task_name,
                provider="openrouter",
                model=model,
            )
            completion = await openrouter.chat_completion(
                model=model,
                messages=attempt_messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = elapsed_ms(started_at)
            content = extract_message_content(completion)
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

        try:
            parsed = _parse_json_content(content, response_model)
        except (ProviderResponseError, ValidationError) as parse_error:
            parse_failure = parse_error
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
                success=False,
                error=f"json_parse_failed (attempt {attempt}/{max_attempts}): {parse_error}",
            )
            if attempt >= max_attempts:
                raise
            attempt_messages = list(base_messages) + _build_retry_followup(
                response_model.__name__, content, parse_error
            )
            continue

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

    assert parse_failure is not None  # loop exits via return or raise on the final attempt
    raise parse_failure


def _parse_json_content(content: str, response_model: type[OutputModel]) -> OutputModel:
    try:
        payload = json.loads(_strip_code_fences(content))
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("OpenRouter response content was not valid JSON") from exc

    validation_error: ValidationError | None = None
    for candidate_payload in _payload_candidates(payload, response_model):
        try:
            return response_model.model_validate(candidate_payload)
        except ValidationError as exc:
            if validation_error is None:
                validation_error = exc

    if validation_error is not None:
        raise validation_error
    raise ProviderResponseError("OpenRouter response content was empty")


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    text = text[3:]
    if text.lower().startswith("json"):
        text = text[4:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _payload_candidates(payload: object, response_model: type[BaseModel]) -> list[object]:
    candidates = [payload]

    if isinstance(payload, dict):
        for wrapper_key in _wrapper_keys(response_model.__name__):
            value = payload.get(wrapper_key)
            if value is not None:
                candidates.append(value)

    single_list_field = _single_list_field_name(response_model)
    if single_list_field is not None:
        candidates.extend(
            {single_list_field: candidate}
            for candidate in list(candidates)
            if isinstance(candidate, list)
        )

    return candidates


def _wrapper_keys(model_name: str) -> tuple[str, ...]:
    return (
        model_name,
        model_name[:1].lower() + model_name[1:],
        _camel_to_snake(model_name),
        "data",
        "result",
        "output",
        "response",
    )


def _camel_to_snake(value: str) -> str:
    with_word_boundaries = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", with_word_boundaries).lower()


def _single_list_field_name(response_model: type[BaseModel]) -> str | None:
    if len(response_model.model_fields) != 1:
        return None

    field_name, field_info = next(iter(response_model.model_fields.items()))
    if get_origin(field_info.annotation) is list:
        return field_name
    return None


def _prepend_schema_instruction(
    messages: list[ChatMessage],
    model_name: str,
    schema_dict: dict[str, object],
) -> list[ChatMessage]:
    required_fields = schema_dict.get("required") if isinstance(schema_dict, dict) else None
    required_summary = (
        f"Required top-level fields: {', '.join(required_fields)}.\n"
        if isinstance(required_fields, list) and required_fields
        else ""
    )
    instruction: ChatMessage = {
        "role": "system",
        "content": render_prompt(
            "llm_router/json_schema_instruction.system.md",
            model_name=model_name,
            required_summary=required_summary.rstrip(),
            schema_json=json.dumps(schema_dict, ensure_ascii=False),
        ),
    }
    return [instruction, *messages]


def _build_retry_followup(
    model_name: str,
    bad_content: str,
    parse_error: Exception,
) -> list[ChatMessage]:
    return [
        {"role": "assistant", "content": bad_content},
        {
            "role": "user",
            "content": render_prompt(
                "llm_router/json_retry.user.md",
                model_name=model_name,
                parse_error=parse_error,
            ),
        },
    ]
