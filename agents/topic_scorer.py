import json
from collections.abc import Sequence
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from repositories.topics import create_scored_topic
from schemas.trend import TopicCandidateInput, TopicScoreOutput
from services.errors import BudgetExceededError, ProviderResponseError, ServiceConfigurationError
from services.llm_router import call_openrouter_json
from services.monitoring import log_run_event
from services.openrouter_client import ChatMessage
from services.prompts import load_prompt

TOPIC_SCORING_TASK_NAME = "topic_scoring"
FATAL_TOPIC_SCORING_EXCEPTIONS = (BudgetExceededError, ServiceConfigurationError)
PROMPT_DIR = "topic_scorer"


async def score_and_store_topics(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_inputs: Sequence[TopicCandidateInput],
) -> list[TopicScoreOutput]:
    scored_topics: list[TopicScoreOutput] = []

    for topic_input in topic_inputs:
        try:
            score = await score_topic_candidate(
                settings=settings,
                db=db,
                run_id=run_id,
                topic_input=topic_input,
            )
        except (ProviderResponseError, ValidationError) as exc:
            score = build_fallback_topic_score(topic_input=topic_input, error=exc)
            log_run_event(
                event="topic_scoring_fallback",
                run_id=run_id,
                task_name=TOPIC_SCORING_TASK_NAME,
                status="warning",
                message=(
                    "Topic scoring provider returned invalid structured output; "
                    f"stored fallback topic for seed query {topic_input.seed_query!r}."
                ),
            )
        create_scored_topic(db, run_id=run_id, score=score)
        scored_topics.append(score)

    return scored_topics


async def score_topic_candidate(
    *,
    settings: Settings,
    db: Session | None,
    run_id: UUID,
    topic_input: TopicCandidateInput,
) -> TopicScoreOutput:
    try:
        return await call_openrouter_json(
            settings=settings,
            model=settings.topic_scoring_model,
            messages=_topic_scoring_messages(topic_input),
            task_name=TOPIC_SCORING_TASK_NAME,
            response_model=TopicScoreOutput,
            db=db,
            run_id=run_id,
            temperature=0.1,
            max_attempts=1,
        )
    except FATAL_TOPIC_SCORING_EXCEPTIONS:
        raise
    except (ProviderResponseError, ValidationError) as exc:
        _log_topic_scoring_fallback(run_id=run_id, topic_input=topic_input)
        return build_fallback_topic_score(topic_input=topic_input, error=exc)
    except Exception as exc:
        _log_topic_scoring_fallback(run_id=run_id, topic_input=topic_input)
        return build_fallback_topic_score(topic_input=topic_input, error=exc)


def _topic_scoring_messages(topic_input: TopicCandidateInput) -> list[ChatMessage]:
    payload = topic_input.model_dump(mode="json")
    return [
        {
            "role": "system",
            "content": _prompt("score_candidate.system.md"),
        },
        {
            "role": "user",
            "content": f"{_prompt('score_candidate.user.md')}\n{json.dumps(payload, ensure_ascii=False)}",
        },
    ]


def _prompt(file_name: str) -> str:
    return load_prompt(f"{PROMPT_DIR}/{file_name}")


def build_fallback_topic_score(
    *,
    topic_input: TopicCandidateInput,
    error: Exception,
) -> TopicScoreOutput:
    title = _fallback_title(topic_input)
    target_keyword = topic_input.seed_query.strip() or title
    search_intent = "comparison" if _looks_like_comparison(title, target_keyword) else "informational"
    trend_score = 35 + min(len(topic_input.candidate_titles), 5) * 5
    orbichat_relevance_score = 45 if _is_orbichat_adjacent(title, target_keyword) else 30
    seo_score = 35
    conversion_score = 25
    total_score = round(
        (trend_score + orbichat_relevance_score + seo_score + conversion_score) / 4
    )

    return TopicScoreOutput(
        title=title,
        target_keyword=target_keyword,
        search_intent=search_intent,
        trend_score=trend_score,
        orbichat_relevance_score=orbichat_relevance_score,
        seo_score=seo_score,
        conversion_score=conversion_score,
        total_score=total_score,
        recommended=False,
        reasoning=(
            "Fallback score created because the topic scoring provider returned invalid structured "
            f"output: {_summarize_error(error)}"
        ),
        cta_angle="Review manually in OrbiChat before draft generation.",
    )


def _log_topic_scoring_fallback(*, run_id: UUID, topic_input: TopicCandidateInput) -> None:
    log_run_event(
        event="topic_scoring_fallback",
        run_id=run_id,
        task_name=TOPIC_SCORING_TASK_NAME,
        status="warning",
        message=(
            "Topic scoring provider returned invalid structured output; "
            f"using fallback topic for seed query {topic_input.seed_query!r}."
        ),
    )


def _fallback_title(topic_input: TopicCandidateInput) -> str:
    for candidate_title in topic_input.candidate_titles:
        normalized = candidate_title.strip()
        if normalized:
            return normalized[:180]
    return (topic_input.seed_query.strip() or "Untitled AI topic")[:180]


def _looks_like_comparison(*values: str) -> bool:
    joined = " ".join(values).lower()
    return any(marker in joined for marker in (" vs ", " versus ", "compare", "comparison"))


def _is_orbichat_adjacent(*values: str) -> bool:
    joined = " ".join(values).lower()
    return any(
        marker in joined
        for marker in (
            "ai chat",
            "chatgpt",
            "claude",
            "gemini",
            "grok",
            "llm",
            "multi-model",
            "model",
            "openrouter",
        )
    )


def _summarize_error(error: Exception) -> str:
    text = str(error).replace("\n", " ").strip()
    return text[:240] + ("..." if len(text) > 240 else "")
