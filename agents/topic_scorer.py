import json
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from repositories.topics import create_scored_topic
from schemas.trend import TopicCandidateInput, TopicScoreOutput
from services.llm_router import call_openrouter_json
from services.openrouter_client import ChatMessage

TOPIC_SCORING_TASK_NAME = "topic_scoring"


async def score_and_store_topics(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_inputs: Sequence[TopicCandidateInput],
) -> list[TopicScoreOutput]:
    scored_topics: list[TopicScoreOutput] = []

    for topic_input in topic_inputs:
        score = await score_topic_candidate(
            settings=settings,
            db=db,
            run_id=run_id,
            topic_input=topic_input,
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
    return await call_openrouter_json(
        settings=settings,
        model=settings.topic_scoring_model,
        messages=_topic_scoring_messages(topic_input),
        task_name=TOPIC_SCORING_TASK_NAME,
        response_model=TopicScoreOutput,
        db=db,
        run_id=run_id,
        temperature=0.2,
    )


def _topic_scoring_messages(topic_input: TopicCandidateInput) -> list[ChatMessage]:
    payload = topic_input.model_dump(mode="json")
    return [
        {
            "role": "system",
            "content": (
                "You score blog topic opportunities for OrbiChat.ai, a multi-model AI chat platform. "
                "Return only structured JSON matching the provided schema. Use scores from 0 to 100."
            ),
        },
        {
            "role": "user",
            "content": (
                "Score this trend cluster for organic search, OrbiChat relevance, and conversion potential. "
                "Prefer practical topics around AI chat, model comparisons, productivity, students, writers, "
                "developers, and multi-model workflows.\n\n"
                f"{json.dumps(payload, ensure_ascii=False)}"
            ),
        },
    ]
