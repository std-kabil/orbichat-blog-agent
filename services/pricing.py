from decimal import Decimal

from app.config import Settings
from services.openrouter_client import ChatMessage

DEFAULT_OUTPUT_TOKEN_ESTIMATE = 1000
CHARS_PER_TOKEN_ESTIMATE = 4
MILLION = Decimal("1000000")


def estimate_message_tokens(messages: list[ChatMessage]) -> int:
    total_chars = sum(len(message.get("content", "")) for message in messages)
    return max(1, total_chars // CHARS_PER_TOKEN_ESTIMATE)


def estimate_llm_call_cost(
    *,
    settings: Settings,
    model: str,
    messages: list[ChatMessage],
    max_tokens: int | None = None,
) -> Decimal:
    return calculate_llm_cost(
        settings=settings,
        model=model,
        input_tokens=estimate_message_tokens(messages),
        output_tokens=max_tokens or DEFAULT_OUTPUT_TOKEN_ESTIMATE,
    )


def calculate_llm_cost(
    *,
    settings: Settings,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    pricing = settings.llm_model_pricing.get(model, {})
    input_per_million = _decimal(pricing.get("input_per_million"))
    output_per_million = _decimal(pricing.get("output_per_million"))
    return (
        Decimal(input_tokens) * input_per_million
        + Decimal(output_tokens) * output_per_million
    ) / MILLION


def calculate_search_cost(*, settings: Settings, provider: str) -> Decimal:
    return _decimal(settings.search_provider_pricing.get(provider))


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
