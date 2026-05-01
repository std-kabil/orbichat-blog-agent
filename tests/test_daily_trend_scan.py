from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from agents.orchestrator import run_daily_trend_scan
from agents.trend_discovery import (
    SEED_QUERIES,
    dedupe_trend_candidates,
    discover_trend_candidates,
    group_topic_candidates,
)
from app.config import Settings
from jobs.daily_trend_scan import daily_trend_scan
from schemas.common import RunType, SearchProvider
from schemas.search import NormalizedSearchResult, SearchProviderWarning, SearchRouterResult
from schemas.trend import TopicCandidateInput, TopicScoreOutput, TrendCandidateCreate
from services.errors import ServiceConfigurationError


class FakeSearchRouter:
    def __init__(self, result: SearchRouterResult) -> None:
        self.result = result
        self.queries: list[str] = []

    async def search(
        self,
        *,
        query: str,
        max_results_per_provider: int = 10,
        db: Session | None = None,
        run_id: UUID | None = None,
        topic_id: UUID | None = None,
        draft_id: UUID | None = None,
    ) -> SearchRouterResult:
        self.queries.append(query)
        return self.result


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _candidate(title: str, url: str | None, query: str = "AI chat apps") -> TrendCandidateCreate:
    return TrendCandidateCreate(
        run_id=uuid4(),
        title=title,
        query=query,
        source=SearchProvider.TAVILY,
        url=url,
        snippet="Snippet",
        detected_at=datetime(2026, 4, 30, tzinfo=UTC),
        metadata_json={},
    )


def _score(title: str = "Best AI chat apps") -> TopicScoreOutput:
    return TopicScoreOutput(
        title=title,
        target_keyword="best AI chat apps",
        search_intent="commercial",
        trend_score=80,
        orbichat_relevance_score=90,
        seo_score=70,
        conversion_score=85,
        total_score=82,
        recommended=True,
        reasoning="Strong OrbiChat fit.",
        cta_angle="Try multiple models in OrbiChat.",
    )


def test_seed_queries_are_stable_and_non_empty() -> None:
    assert len(SEED_QUERIES) == 14
    assert "ChatGPT alternatives" in SEED_QUERIES
    assert "multi-model AI chat" in SEED_QUERIES


@pytest.mark.anyio
async def test_search_results_become_trend_candidates(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    created_candidates: list[TrendCandidateCreate] = []
    run_id = uuid4()
    result = SearchRouterResult(
        results=[
            NormalizedSearchResult(
                title="AI chat apps are changing",
                url="https://example.com/ai-chat",
                snippet="Useful summary",
                published_at=datetime(2026, 4, 30, tzinfo=UTC),
                source_provider=SearchProvider.TAVILY,
                raw={"id": "1"},
            )
        ],
        warnings=[
            SearchProviderWarning(provider=SearchProvider.EXA, message="timeout"),
            SearchProviderWarning(provider=SearchProvider.EXA, message="timeout"),
        ],
    )

    def fake_create(db: object, candidates: list[TrendCandidateCreate]) -> list[object]:
        created_candidates.extend(candidates)
        return []

    monkeypatch.setattr("agents.trend_discovery.create_trend_candidates", fake_create)

    candidates, warnings, skipped = await discover_trend_candidates(
        settings=Settings(
            app_env="test",
            tavily_api_key="tavily",
            exa_api_key=None,
            brave_api_key=None,
            sentry_dsn=None,
        ),
        db=cast(Session, SimpleNamespace()),
        run_id=run_id,
        search_router=FakeSearchRouter(result),
        seed_queries=("AI chat apps",),
    )

    assert candidates == created_candidates
    assert candidates[0].title == "AI chat apps are changing"
    assert candidates[0].run_id == run_id
    assert candidates[0].source is SearchProvider.TAVILY
    assert len(warnings) == 1
    assert skipped == [SearchProvider.EXA, SearchProvider.BRAVE]


@pytest.mark.anyio
async def test_discovery_fails_when_no_search_provider_is_configured() -> None:
    with pytest.raises(ServiceConfigurationError):
        await discover_trend_candidates(
            settings=Settings(
                app_env="test",
                tavily_api_key=None,
                exa_api_key=None,
                brave_api_key=None,
                sentry_dsn=None,
            ),
            db=cast(Session, SimpleNamespace()),
            run_id=uuid4(),
            seed_queries=("AI chat apps",),
        )


def test_dedupe_candidates_prefers_url_then_title() -> None:
    first = _candidate("AI Chat Apps", "https://example.com/post?utm_source=x&a=1")
    duplicate_url = _candidate("Different title", "https://example.com/post?a=1#section")
    duplicate_title = _candidate("AI chat apps", None)
    unique = _candidate("Claude vs GPT", "https://example.com/claude")

    deduped = dedupe_trend_candidates([first, duplicate_url, duplicate_title, unique])

    assert deduped == [first, unique]


def test_group_topic_candidates_creates_topic_inputs() -> None:
    grouped = group_topic_candidates(
        [
            _candidate("Best AI chat apps in 2026", "https://example.com/a"),
            _candidate("AI chat app comparison", "https://example.com/b"),
            _candidate("Claude vs GPT for coding", "https://example.com/c", query="Claude vs GPT"),
        ]
    )

    assert all(isinstance(topic_input, TopicCandidateInput) for topic_input in grouped)
    assert grouped[0].seed_query == "AI chat apps"
    assert grouped[0].candidate_titles


@pytest.mark.anyio
async def test_orchestrator_marks_completed_and_preserves_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = uuid4()
    calls: list[str] = []

    async def fake_discover(**kwargs: object) -> tuple[
        list[TrendCandidateCreate],
        list[SearchProviderWarning],
        list[SearchProvider],
    ]:
        return (
            [_candidate("AI chat apps", "https://example.com/a")],
            [SearchProviderWarning(provider=SearchProvider.EXA, message="timeout")],
            [SearchProvider.BRAVE],
        )

    async def fake_score(**kwargs: object) -> list[TopicScoreOutput]:
        return [_score()]

    monkeypatch.setattr("agents.orchestrator.discover_trend_candidates", fake_discover)
    monkeypatch.setattr("agents.orchestrator.score_and_store_topics", fake_score)
    monkeypatch.setattr("agents.orchestrator.mark_run_running", lambda db, run_id: calls.append("running"))
    monkeypatch.setattr(
        "agents.orchestrator.mark_run_completed",
        lambda db, run_id, metadata_json: calls.append(f"completed:{metadata_json['topic_count']}"),
    )
    monkeypatch.setattr("agents.orchestrator.update_run_totals", lambda db, run_id, costs: None)
    monkeypatch.setattr(
        "agents.orchestrator.summarize_costs",
        lambda db, run_id: SimpleNamespace(
            total_estimated_cost_usd=0,
            total_input_tokens=0,
            total_output_tokens=0,
        ),
    )

    result = await run_daily_trend_scan(
        settings=Settings(app_env="test", tavily_api_key="tavily", openrouter_api_key="openrouter"),
        db=cast(Session, SimpleNamespace()),
        run_id=run_id,
    )

    assert result.topic_count == 1
    assert result.provider_warnings == ["exa: timeout"]
    assert result.skipped_providers == ["brave"]
    assert calls == ["running", "completed:1"]


@pytest.mark.anyio
async def test_orchestrator_marks_failed_when_scoring_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = uuid4()
    calls: list[str] = []

    async def fake_discover(**kwargs: object) -> tuple[
        list[TrendCandidateCreate],
        list[SearchProviderWarning],
        list[SearchProvider],
    ]:
        return ([_candidate("AI chat apps", "https://example.com/a")], [], [])

    async def fake_score(**kwargs: object) -> list[TopicScoreOutput]:
        raise RuntimeError("scoring failed")

    monkeypatch.setattr("agents.orchestrator.discover_trend_candidates", fake_discover)
    monkeypatch.setattr("agents.orchestrator.score_and_store_topics", fake_score)
    monkeypatch.setattr("agents.orchestrator.mark_run_running", lambda db, run_id: calls.append("running"))
    monkeypatch.setattr(
        "agents.orchestrator.mark_run_failed",
        lambda db, run_id, error_message: calls.append(f"failed:{error_message}"),
    )

    with pytest.raises(RuntimeError, match="scoring failed"):
        await run_daily_trend_scan(
            settings=Settings(app_env="test", tavily_api_key="tavily", openrouter_api_key="openrouter"),
            db=cast(Session, SimpleNamespace()),
            run_id=run_id,
        )

    assert calls == ["running", "failed:scoring failed"]


def test_daily_job_creates_run_when_scheduled_without_run_id(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_session = FakeSession()
    run_id = uuid4()
    calls: list[object] = []

    def fake_create_run(db: object, run_type: object) -> SimpleNamespace:
        calls.append(run_type)
        return SimpleNamespace(id=run_id)

    monkeypatch.setattr("jobs.daily_trend_scan.SessionLocal", lambda: fake_session)
    monkeypatch.setattr("jobs.daily_trend_scan.get_settings", lambda: Settings(app_env="test"))
    monkeypatch.setattr("jobs.daily_trend_scan.create_run", fake_create_run)
    monkeypatch.setattr(
        "jobs.daily_trend_scan.run_daily_trend_scan",
        lambda **kwargs: _async_return(
            SimpleNamespace(
                model_dump=lambda mode: {
                    "run_id": str(kwargs["run_id"]),
                    "status": "completed",
                }
            )
        ),
    )

    result = daily_trend_scan()

    assert result["run_id"] == str(run_id)
    assert result["status"] == "completed"
    assert calls == [RunType.DAILY_SCAN]
    assert fake_session.closed is True


async def _async_return(value: object) -> object:
    return value
