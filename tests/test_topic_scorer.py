from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from agents.topic_scorer import score_and_store_topics, score_topic_candidate
from app.config import Settings
from schemas.trend import TopicCandidateInput, TopicScoreOutput


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
