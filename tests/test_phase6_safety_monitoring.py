from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.publish_checks import run_deterministic_publish_checks
from app.config import Settings
from app.dependencies import get_database_session
from app.main import create_app
from schemas.common import SearchProvider
from schemas.workflow import ClaimVerificationOutput, DraftSafetyReport, FactCheckSummary
from services.budget import assert_budget_available
from services.errors import BudgetExceededError
from services.llm_router import call_openrouter_json
from services.monitoring import capture_run_exception, log_run_event
from services.openrouter_client import OpenRouterClient
from services.pricing import calculate_llm_cost, calculate_search_cost, estimate_llm_call_cost
from services.search_router import SearchRouter
from services.tavily_client import TavilySearchClient


class ExampleResponse(BaseModel):
    answer: str


class FakeExecuteResult:
    def __init__(self, value: Decimal) -> None:
        self.value = value

    def scalar_one(self) -> Decimal:
        return self.value


class FakeBudgetSession:
    def __init__(self, spend: Decimal = Decimal("0")) -> None:
        self.spend = spend
        self.added: list[object] = []

    def execute(self, statement: object) -> FakeExecuteResult:
        return FakeExecuteResult(self.spend)

    def add(self, item: object) -> None:
        self.added.append(item)

    def commit(self) -> None:
        return None

    def refresh(self, item: object) -> None:
        return None


class InvokedSearchClient:
    def __init__(self) -> None:
        self.invoked = False

    async def search(self, **kwargs: object) -> list[object]:
        self.invoked = True
        return []


class NeverInvokedOpenRouterClient:
    async def chat_completion(self, **kwargs: object) -> object:
        raise AssertionError("OpenRouter client should not be invoked")


def _verification(**overrides: object) -> ClaimVerificationOutput:
    values: dict[str, object] = {
        "claim": "The app costs $10.",
        "claim_type": "pricing",
        "verdict": "unsupported",
        "severity": "medium",
        "source_urls": [],
        "explanation": "Pricing claim lacks source.",
        "recommended_action": "remove",
    }
    values.update(overrides)
    return ClaimVerificationOutput.model_validate(values)


def test_pricing_defaults_and_init_override() -> None:
    settings = Settings(
        llm_model_pricing={
            "test/model": {
                "input_per_million": Decimal("1"),
                "output_per_million": Decimal("2"),
            }
        },
        search_provider_pricing={"tavily": Decimal("0.25")},
    )

    assert calculate_llm_cost(
        settings=settings,
        model="test/model",
        input_tokens=1_000_000,
        output_tokens=500_000,
    ) == Decimal("2")
    assert calculate_search_cost(settings=settings, provider="tavily") == Decimal("0.25")
    assert Settings().search_provider_pricing["brave"] > 0


def test_pricing_env_override_parses_json(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv(
        "LLM_MODEL_PRICING",
        '{"env/model":{"input_per_million":"1.5","output_per_million":"2.5"}}',
    )
    monkeypatch.setenv("SEARCH_PROVIDER_PRICING", '{"tavily":"0.125"}')

    settings = Settings()

    assert settings.llm_model_pricing["env/model"]["input_per_million"] == Decimal("1.5")
    assert settings.search_provider_pricing["tavily"] == Decimal("0.125")


def test_llm_estimated_cost_uses_message_and_output_tokens() -> None:
    settings = Settings(
        llm_model_pricing={
            "test/model": {
                "input_per_million": Decimal("4"),
                "output_per_million": Decimal("8"),
            }
        }
    )

    cost = estimate_llm_call_cost(
        settings=settings,
        model="test/model",
        messages=[{"role": "user", "content": "x" * 400}],
        max_tokens=100,
    )

    assert cost == Decimal("0.0012")


def test_budget_guard_blocks_daily_limit() -> None:
    with pytest.raises(BudgetExceededError, match="Daily budget exceeded"):
        assert_budget_available(
            settings=Settings(agent_daily_budget_usd=Decimal("1.00")),
            db=cast(Session, FakeBudgetSession(spend=Decimal("0.99"))),
            estimated_cost_usd=Decimal("0.02"),
            run_id=uuid4(),
            task_name="test",
            provider="openrouter",
            model="test/model",
        )


@pytest.mark.anyio
async def test_openrouter_call_is_blocked_before_client_invocation() -> None:
    with pytest.raises(BudgetExceededError):
        await call_openrouter_json(
            settings=Settings(
                openrouter_api_key="key",
                agent_daily_budget_usd=Decimal("0.000001"),
                llm_model_pricing={
                    "test/model": {
                        "input_per_million": Decimal("100"),
                        "output_per_million": Decimal("100"),
                    }
                },
            ),
            model="test/model",
            messages=[{"role": "user", "content": "hello"}],
            task_name="budgeted_json",
            response_model=ExampleResponse,
            db=cast(Session, FakeBudgetSession()),
            client=cast(OpenRouterClient, NeverInvokedOpenRouterClient()),
        )


@pytest.mark.anyio
async def test_search_call_is_blocked_before_provider_client_invocation() -> None:
    client = InvokedSearchClient()
    router = SearchRouter(
        Settings(
            tavily_api_key="key",
            exa_api_key=None,
            brave_api_key=None,
            agent_daily_budget_usd=Decimal("0.001"),
            search_provider_pricing={"tavily": Decimal("0.01")},
        ),
        tavily_client=cast(TavilySearchClient, client),
    )

    result = await router.search(query="ai", db=cast(Session, FakeBudgetSession()))

    assert client.invoked is False
    assert result.results == []
    assert result.warnings[0].provider is SearchProvider.TAVILY
    assert "budget exceeded" in result.warnings[0].message.lower()


def test_publish_safety_blocks_unverified_pricing_claim() -> None:
    checks = run_deterministic_publish_checks(
        settings=Settings(auto_publish=True),
        title="Best AI Chat Apps",
        slug="best-ai-chat-apps",
        meta_description="A practical guide.",
        markdown_content="# Title\n\n" + " ".join(["useful"] * 920),
        verifications=[_verification()],
    )

    assert checks.publish_ready is False
    assert "Article includes direct pricing/benchmark claims without source verification" in checks.blockers


def test_publish_safety_blocks_fake_citations_and_placeholders() -> None:
    checks = run_deterministic_publish_checks(
        settings=Settings(auto_publish=True),
        title="Best AI Chat Apps",
        slug="best-ai-chat-apps",
        meta_description="A practical guide.",
        markdown_content="# Title\n\nTODO " + " ".join(["useful"] * 920) + " [citation needed]",
        verifications=[_verification(verdict="supported", source_urls=["https://example.com"])],
    )

    assert "Article contains placeholder text" in checks.blockers
    assert "Article uses fake citations" in checks.blockers


def test_safety_report_endpoint_returns_summary(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 4, 30, tzinfo=UTC)
    draft_id = uuid4()
    draft = SimpleNamespace(
        id=draft_id,
        publish_ready=False,
        publish_score=72,
        seo_json={
            "publish_safety": {
                "deterministic_blockers": ["AUTO_PUBLISH is false"],
                "required_fixes": ["Add citations"],
                "reasoning": "Needs source work.",
            }
        },
    )
    fact_check = SimpleNamespace(
        verdict="unsupported",
        severity="high",
    )

    app = create_app(Settings(app_env="test", sentry_dsn=None))
    app.dependency_overrides[get_database_session] = lambda: object()
    monkeypatch.setattr("api.routes_drafts.get_draft", lambda db, draft_id: draft)
    monkeypatch.setattr("api.routes_drafts.list_fact_checks_by_draft", lambda db, draft_id: [fact_check])

    response = TestClient(app).get(f"/drafts/{draft_id}/safety-report")

    assert response.status_code == 200
    body = response.json()
    assert body["deterministic_blockers"] == ["AUTO_PUBLISH is false"]
    assert body["fact_check_summary"]["high_severity_unsupported"] == 1
    assert now.year == 2026


def test_publish_judgment_endpoint_uses_safety_service(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    draft_id = uuid4()
    report = DraftSafetyReport(
        draft_id=draft_id,
        publish_ready=False,
        publish_score=80,
        deterministic_blockers=["AUTO_PUBLISH is false"],
        required_fixes=[],
        fact_check_summary=FactCheckSummary(
            total=0,
            supported=0,
            unsupported=0,
            unclear=0,
            opinion=0,
            high_severity_unsupported=0,
            medium_severity_unclear=0,
        ),
        reasoning="Blocked by config.",
    )

    async def fake_safety_service(**kwargs: object) -> DraftSafetyReport:
        return report

    app = create_app(Settings(app_env="test", sentry_dsn=None))
    app.dependency_overrides[get_database_session] = lambda: object()
    monkeypatch.setattr("api.routes_drafts.run_publish_safety_for_draft", fake_safety_service)

    response = TestClient(app).post(f"/drafts/{draft_id}/publish-judgment")

    assert response.status_code == 200
    assert response.json()["publish_score"] == 80


def test_monitoring_skips_sentry_in_test(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: list[Exception] = []
    logs: list[dict[str, object]] = []

    monkeypatch.setattr("services.monitoring.sentry_sdk.capture_exception", lambda exc: captured.append(exc))

    class FakeLogger:
        def bind(self, **kwargs: object) -> "FakeLogger":
            logs.append(kwargs)
            return self

        def info(self, message: str) -> None:
            return None

        def warning(self, message: str) -> None:
            return None

        def error(self, message: str) -> None:
            return None

    monkeypatch.setattr("services.monitoring.logger", FakeLogger())
    log_run_event(event="test", run_id=uuid4(), status="completed")
    capture_run_exception(settings=Settings(app_env="test", sentry_dsn="https://example.com/1"), exc=RuntimeError("x"))

    assert logs[0]["status"] == "completed"
    assert captured == []
