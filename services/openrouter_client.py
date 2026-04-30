from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, InternalServerError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings
from services.errors import ProviderResponseError, ServiceConfigurationError

ChatMessage = dict[str, str]


class OpenRouterClient:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.openrouter_api_key:
            raise ServiceConfigurationError("OPENROUTER_API_KEY is required for model calls")

        # The OpenAI SDK returns dynamic response objects, so injected test clients use the same surface.
        self._client: Any = client or AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        response_format: dict[str, object] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> object:
        kwargs: dict[str, object] = {
            "model": model,
            "messages": messages,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        return await self._client.chat.completions.create(**kwargs)


def extract_message_content(completion: object) -> str:
    choices = _read_field(completion, "choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderResponseError("OpenRouter response did not include choices")

    first_choice = choices[0]
    message = _read_field(first_choice, "message")
    content = _read_field(message, "content")
    if not isinstance(content, str) or not content:
        raise ProviderResponseError("OpenRouter response did not include message content")

    return content


def _read_field(container: object, key: str) -> object:
    if isinstance(container, dict):
        return container.get(key)
    return getattr(container, key, None)
