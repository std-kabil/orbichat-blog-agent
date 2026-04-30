from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy.orm import Session

from agents.topic_scorer import (
    FATAL_TOPIC_SCORING_EXCEPTIONS,
    build_fallback_topic_score,
    score_and_store_topics,
    score_topic_candidate,
)
from app.config import Settings
from schemas.trend import TopicCandidateInput, TopicScoreOutput
from services.errors import BudgetExceededError, ProviderResponseError


def _topic_input() -> TopicCandidateInput:
    return TopicCandidateInput(
        seed_query="AI chat apps",
        candidate_titles=["Best AI chat apps"],
        snippets=["Comparison of popular AI chat tools."],
        source_urls=["https://example.com/ai-chat"],
    )


def _score() -> TopicScoreOutput:
    return TopicScoreOutput(
        title="Best AI chat apps",
        target_keyword="best AI chat apps",
        search_intent="commercial",
        trend_score=80,
        orbichat_relevance_score=90,
        seo_score=70,
        conversion_score=85,
        total_score=82,
        recommended=True,
        reasoning="Strong fit.",
        cta_angle="Compare models in OrbiChat.",
    )


@pytest.mark.anyio
async def test_topic_scoring_validates_structured_output(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_call_openrouter_json(**kwargs: object) -> TopicScoreOutput:
        assert kwargs["model"] == "qwen/qwen3.6-plus"
        assert kwargs["response_model"] is TopicScoreOutput
        assert kwargs["max_attempts"] == 1
        return _score()

    monkeypatch.setattr("agents.topic_scorer.call_openrouter_json", fake_call_openrouter_json)

    score = await score_topic_candidate(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=None,
        run_id=uuid4(),
        topic_input=_topic_input(),
    )

    assert score.total_score == 82
    assert score.recommended is True


@pytest.mark.anyio
async def test_score_topic_candidate_falls_back_without_paid_retry(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls = 0

    async def fake_call_openrouter_json(**kwargs: object) -> TopicScoreOutput:
        nonlocal calls
        calls += 1
        assert kwargs["max_attempts"] == 1
        raise ProviderResponseError("wrong response shape")

    monkeypatch.setattr("agents.topic_scorer.call_openrouter_json", fake_call_openrouter_json)

    score = await score_topic_candidate(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=None,
        run_id=uuid4(),
        topic_input=_topic_input(),
    )

    assert calls == 1
    assert score.recommended is False
    assert score.title == "Best AI chat apps"


@pytest.mark.anyio
async def test_score_topic_candidate_falls_back_on_topic_score_validation_error(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_call_openrouter_json(**kwargs: object) -> TopicScoreOutput:
        TopicScoreOutput.model_validate(
            {
                "organic_search_score": 72,
                "orbichat_fit_score": 81,
                "conversion_potential_score": 64,
                "recommended_angles": ["practical benchmarks"],
            }
        )
        raise AssertionError("partial provider response should not validate")

    monkeypatch.setattr("agents.topic_scorer.call_openrouter_json", fake_call_openrouter_json)

    score = await score_topic_candidate(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=None,
        run_id=uuid4(),
        topic_input=_topic_input(),
    )

    assert score.title == "Best AI chat apps"
    assert score.target_keyword == "AI chat apps"
    assert score.recommended is False
    assert "provider returned invalid structured output" in score.reasoning


@pytest.mark.anyio
async def test_score_topic_candidate_falls_back_on_unexpected_provider_error(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_call_openrouter_json(**kwargs: object) -> TopicScoreOutput:
        raise RuntimeError("provider returned malformed topic score")

    monkeypatch.setattr("agents.topic_scorer.call_openrouter_json", fake_call_openrouter_json)

    score = await score_topic_candidate(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=None,
        run_id=uuid4(),
        topic_input=_topic_input(),
    )

    assert score.title == "Best AI chat apps"
    assert score.recommended is False
    assert "provider returned malformed topic score" in score.reasoning


@pytest.mark.anyio
async def test_score_topic_candidate_does_not_fallback_on_budget_error(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_call_openrouter_json(**kwargs: object) -> TopicScoreOutput:
        raise BudgetExceededError("Daily budget exceeded")

    monkeypatch.setattr("agents.topic_scorer.call_openrouter_json", fake_call_openrouter_json)

    with pytest.raises(FATAL_TOPIC_SCORING_EXCEPTIONS):
        await score_topic_candidate(
            settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
            db=None,
            run_id=uuid4(),
            topic_input=_topic_input(),
        )


@pytest.mark.anyio
async def test_score_and_store_topics_persists_scores(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    stored_titles: list[str] = []

    async def fake_score_topic_candidate(**kwargs: object) -> TopicScoreOutput:
        return _score()

    def fake_create_scored_topic(db: object, *, run_id: object, score: TopicScoreOutput) -> object:
        stored_titles.append(score.title)
        return object()

    monkeypatch.setattr("agents.topic_scorer.score_topic_candidate", fake_score_topic_candidate)
    monkeypatch.setattr("agents.topic_scorer.create_scored_topic", fake_create_scored_topic)

    scores = await score_and_store_topics(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=cast(Session, SimpleNamespace()),
        run_id=uuid4(),
        topic_inputs=[_topic_input()],
    )

    assert [score.title for score in scores] == ["Best AI chat apps"]
    assert stored_titles == ["Best AI chat apps"]


@pytest.mark.anyio
async def test_score_and_store_topics_falls_back_on_invalid_provider_output(
    monkeypatch: MonkeyPatch,
) -> None:
    stored_scores: list[TopicScoreOutput] = []

    async def fake_score_topic_candidate(**kwargs: object) -> TopicScoreOutput:
        raise ProviderResponseError("OpenRouter response content was not valid JSON")

    def fake_create_scored_topic(db: object, *, run_id: object, score: TopicScoreOutput) -> object:
        stored_scores.append(score)
        return object()

    monkeypatch.setattr("agents.topic_scorer.score_topic_candidate", fake_score_topic_candidate)
    monkeypatch.setattr("agents.topic_scorer.create_scored_topic", fake_create_scored_topic)

    scores = await score_and_store_topics(
        settings=Settings(app_env="test", openrouter_api_key="openrouter", sentry_dsn=None),
        db=cast(Session, SimpleNamespace()),
        run_id=uuid4(),
        topic_inputs=[_topic_input()],
    )

    assert len(scores) == 1
    assert scores[0].title == "Best AI chat apps"
    assert scores[0].recommended is False
    assert "Fallback score" in scores[0].reasoning
    assert stored_scores == scores


def test_build_fallback_topic_score_uses_comparison_intent() -> None:
    score = build_fallback_topic_score(
        topic_input=TopicCandidateInput(
            seed_query="Gemini vs Grok",
            candidate_titles=["Gemini vs Grok for research"],
            snippets=[],
            source_urls=[],
        ),
        error=ProviderResponseError("bad shape"),
    )

    assert score.search_intent == "comparison"
    assert score.recommended is False
    assert score.total_score > 0
