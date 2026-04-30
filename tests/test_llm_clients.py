from types import SimpleNamespace
from typing import cast

import pytest
from pydantic import BaseModel, ValidationError

from app.config import Settings
from services.errors import ProviderResponseError, ServiceConfigurationError
from services.llm_router import call_openrouter_json, call_openrouter_text
from services.openrouter_client import OpenRouterClient


class ExampleResponse(BaseModel):
    answer: str


class FakeOpenRouterClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.response_format: dict[str, object] | None = None

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, object] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> object:
        self.response_format = response_format
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
        )


def test_openrouter_client_requires_api_key() -> None:
    with pytest.raises(ServiceConfigurationError):
        OpenRouterClient(Settings(openrouter_api_key=None))


@pytest.mark.anyio
async def test_openrouter_text_returns_content_and_logs_usage(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, object]] = []

    def fake_record_llm_call(db: object, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("services.llm_router.record_llm_call", fake_record_llm_call)

    result = await call_openrouter_text(
        settings=Settings(openrouter_api_key="key"),
        model="openai/gpt-5.4-mini",
        messages=[{"role": "user", "content": "hello"}],
        task_name="test_task",
        client=cast(OpenRouterClient, FakeOpenRouterClient("hello back")),
    )

    assert result == "hello back"
    assert calls[0]["success"] is True
    assert getattr(calls[0]["usage"], "input_tokens") == 3
    assert getattr(calls[0]["usage"], "output_tokens") == 4


@pytest.mark.anyio
async def test_openrouter_json_validates_response_model() -> None:
    fake_client = FakeOpenRouterClient('{"answer": "yes"}')

    result = await call_openrouter_json(
        settings=Settings(openrouter_api_key="key"),
        model="openai/gpt-5.4-mini",
        messages=[{"role": "user", "content": "return json"}],
        task_name="json_task",
        response_model=ExampleResponse,
        client=cast(OpenRouterClient, fake_client),
    )

    assert result.answer == "yes"
    assert fake_client.response_format is not None
    assert fake_client.response_format["type"] == "json_schema"


@pytest.mark.anyio
async def test_openrouter_json_invalid_content_logs_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, object]] = []

    def fake_record_llm_call(db: object, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("services.llm_router.record_llm_call", fake_record_llm_call)

    with pytest.raises(ProviderResponseError):
        await call_openrouter_json(
            settings=Settings(openrouter_api_key="key"),
            model="openai/gpt-5.4-mini",
            messages=[{"role": "user", "content": "return json"}],
            task_name="json_task",
            response_model=ExampleResponse,
            client=cast(OpenRouterClient, FakeOpenRouterClient("not-json")),
        )

    assert calls[-1]["success"] is False


@pytest.mark.anyio
async def test_openrouter_json_schema_validation_error_logs_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, object]] = []

    def fake_record_llm_call(db: object, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr("services.llm_router.record_llm_call", fake_record_llm_call)

    with pytest.raises(ValidationError):
        await call_openrouter_json(
            settings=Settings(openrouter_api_key="key"),
            model="openai/gpt-5.4-mini",
            messages=[{"role": "user", "content": "return json"}],
            task_name="json_task",
            response_model=ExampleResponse,
            client=cast(OpenRouterClient, FakeOpenRouterClient('{"wrong": "field"}')),
        )

    assert calls[-1]["success"] is False
