import json
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Source, Topic
from schemas.workflow import (
    BlogDraftOutput,
    ClaimExtractionOutput,
    ClaimVerificationBatchOutput,
    ClaimVerificationOutput,
    OutlineOutput,
    PublishJudgmentOutput,
    SEOAnglesOutput,
    SocialPostsOutput,
)
from services.llm_router import call_openrouter_json
from services.openrouter_client import ChatMessage
from services.prompts import load_prompt

PROMPT_DIR = "blog_generation"


async def generate_seo_angles(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic: Topic,
    sources: Sequence[Source],
) -> SEOAnglesOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.seo_angles_model,
        messages=_messages(
            system=_prompt("seo_angles.system.md"),
            user=_prompt("seo_angles.user.md"),
            payload=_topic_payload(topic, sources),
        ),
        task_name="weekly_seo_angles",
        response_model=SEOAnglesOutput,
        db=db,
        run_id=run_id,
        topic_id=topic.id,
        temperature=0.2,
    )


async def generate_outline(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic: Topic,
    sources: Sequence[Source],
    seo_angles: SEOAnglesOutput,
) -> OutlineOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.outline_model,
        messages=_messages(
            system=_prompt("outline.system.md"),
            user=_prompt("outline.user.md"),
            payload={**_topic_payload(topic, sources), "seo_angles": seo_angles.model_dump(mode="json")},
        ),
        task_name="weekly_outline",
        response_model=OutlineOutput,
        db=db,
        run_id=run_id,
        topic_id=topic.id,
        temperature=0.2,
    )


async def write_article_draft(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic: Topic,
    sources: Sequence[Source],
    seo_angles: SEOAnglesOutput,
    outline: OutlineOutput,
) -> BlogDraftOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.article_writing_model,
        messages=_messages(
            system=_prompt("article_draft.system.md"),
            user=_prompt("article_draft.user.md"),
            payload={
                **_topic_payload(topic, sources),
                "seo_angles": seo_angles.model_dump(mode="json"),
                "outline": outline.model_dump(mode="json"),
            },
        ),
        task_name="weekly_article_writing",
        response_model=BlogDraftOutput,
        db=db,
        run_id=run_id,
        topic_id=topic.id,
        temperature=0.4,
    )


async def extract_claims(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID,
    draft: BlogDraftOutput,
) -> ClaimExtractionOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.claim_extraction_model,
        messages=_messages(
            system=_prompt("claim_extraction.system.md"),
            user=_prompt("claim_extraction.user.md"),
            payload=draft.model_dump(mode="json"),
        ),
        task_name="weekly_claim_extraction",
        response_model=ClaimExtractionOutput,
        db=db,
        run_id=run_id,
        topic_id=topic_id,
        temperature=0.0,
    )


async def verify_claims(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID,
    draft_id: UUID | None,
    sources: Sequence[Source],
    claims: ClaimExtractionOutput,
) -> list[ClaimVerificationOutput]:
    if not claims.claims:
        return []

    verification = await call_openrouter_json(
        settings=settings,
        model=settings.risky_claim_review_model,
        messages=_messages(
            system=_prompt("claim_verification.system.md"),
            user=_prompt("claim_verification.user.md"),
            payload={
                "claims": claims.model_dump(mode="json")["claims"],
                "sources": _source_payload(sources),
            },
        ),
        task_name="weekly_claim_verification",
        response_model=ClaimVerificationBatchOutput,
        db=db,
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        temperature=0.0,
    )
    claim_types = {claim.claim: claim.claim_type for claim in claims.claims}
    return [
        item.model_copy(update={"claim_type": item.claim_type or claim_types.get(item.claim)})
        for item in verification.verifications
    ]


async def polish_brand_draft(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID,
    draft_id: UUID | None,
    draft: BlogDraftOutput,
    verifications: Sequence[ClaimVerificationOutput],
) -> BlogDraftOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.brand_polish_model,
        messages=_messages(
            system=_prompt("brand_polish.system.md"),
            user=_prompt("brand_polish.user.md"),
            payload={
                "draft": draft.model_dump(mode="json"),
                "claim_verifications": [item.model_dump(mode="json") for item in verifications],
            },
        ),
        task_name="weekly_brand_polish",
        response_model=BlogDraftOutput,
        db=db,
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        temperature=0.25,
    )


async def generate_social_posts(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID,
    draft_id: UUID,
    draft: BlogDraftOutput,
) -> SocialPostsOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.social_posts_model,
        messages=_messages(
            system=_prompt("social_posts.system.md"),
            user=_prompt("social_posts.user.md"),
            payload=draft.model_dump(mode="json"),
        ),
        task_name="weekly_social_posts",
        response_model=SocialPostsOutput,
        db=db,
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        temperature=0.5,
    )


async def judge_publish_readiness(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID,
    draft_id: UUID,
    draft: BlogDraftOutput,
    deterministic_blockers: Sequence[str],
    verifications: Sequence[ClaimVerificationOutput],
) -> PublishJudgmentOutput:
    return await call_openrouter_json(
        settings=settings,
        model=settings.publish_judgment_model,
        messages=_messages(
            system=_prompt("publish_judgment.system.md"),
            user=_prompt("publish_judgment.user.md"),
            payload={
                "draft": draft.model_dump(mode="json"),
                "deterministic_blockers": list(deterministic_blockers),
                "claim_verifications": [item.model_dump(mode="json") for item in verifications],
            },
        ),
        task_name="weekly_publish_judgment",
        response_model=PublishJudgmentOutput,
        db=db,
        run_id=run_id,
        draft_id=draft_id,
        topic_id=topic_id,
        temperature=0.0,
    )


def _prompt(file_name: str) -> str:
    return load_prompt(f"{PROMPT_DIR}/{file_name}")


def _messages(*, system: str, user: str, payload: object) -> list[ChatMessage]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{user}\n\n{json.dumps(payload, ensure_ascii=False)}"},
    ]


def _topic_payload(topic: Topic, sources: Sequence[Source]) -> dict[str, object]:
    return {
        "topic": {
            "id": str(topic.id),
            "title": topic.title,
            "target_keyword": topic.target_keyword,
            "search_intent": topic.search_intent,
            "summary": topic.summary,
            "reasoning": topic.reasoning,
            "cta_angle": topic.cta_angle,
            "total_score": topic.total_score,
        },
        "sources": _source_payload(sources),
    }


def _source_payload(sources: Sequence[Source]) -> list[dict[str, object]]:
    return [
        {
            "url": source.url,
            "title": source.title,
            "publisher": source.publisher,
            "published_at": source.published_at.isoformat() if source.published_at else None,
            "snippet": source.snippet,
            "source_type": source.source_type,
        }
        for source in sources
    ]
