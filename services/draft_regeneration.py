from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from agents.blog_generation import (
    extract_claims,
    polish_brand_draft,
    regenerate_article_draft,
    review_draft_for_regeneration,
    verify_claims,
)
from agents.publish_checks import run_deterministic_publish_checks
from app.config import Settings
from app.models import BlogDraft, Source
from repositories.drafts import create_draft_revision, get_draft, update_draft_feedback_metadata, update_publish_metadata
from repositories.fact_checks import create_fact_checks_from_verifications
from repositories.runs import create_run, mark_run_completed, mark_run_failed, mark_run_running
from repositories.sources import list_sources_by_draft, list_sources_by_topic
from schemas.common import DraftStatus, RunType
from schemas.workflow import BlogDraftOutput, DraftFeedbackOutput, DraftRegenerationResult
from services.publish_safety import run_publish_safety_for_draft


async def generate_feedback_for_draft(
    *,
    settings: Settings,
    db: Session,
    draft_id: UUID,
) -> DraftFeedbackOutput:
    draft = _require_draft(db, draft_id)
    sources = _sources_for_draft(db, draft)
    run = create_run(db, RunType.VERIFY_DRAFT)
    mark_run_running(db, run.id)
    try:
        feedback = await review_draft_for_regeneration(
            settings=settings,
            db=db,
            run_id=run.id,
            draft_id=draft.id,
            topic=draft.topic,
            draft=_draft_output(draft),
            sources=sources,
            publish_score=draft.publish_score,
        )
        update_draft_feedback_metadata(
            db,
            draft_id=draft.id,
            feedback_metadata=_feedback_metadata(
                feedback=feedback,
                model=settings.blog_feedback_model,
                parent_draft_id=draft.id,
                additional_instructions=None,
            ),
        )
        mark_run_completed(db, run.id, {"draft_id": str(draft.id), "task": "draft_feedback"})
        return feedback
    except Exception as exc:
        mark_run_failed(db, run.id, str(exc))
        raise


async def regenerate_draft_with_feedback(
    *,
    settings: Settings,
    db: Session,
    draft_id: UUID,
    additional_instructions: str | None,
) -> DraftRegenerationResult:
    parent = _require_draft(db, draft_id)
    sources = _sources_for_draft(db, parent)
    run = create_run(db, RunType.MANUAL_DRAFT)
    mark_run_running(db, run.id)

    try:
        current = _draft_output(parent)
        feedback = await review_draft_for_regeneration(
            settings=settings,
            db=db,
            run_id=run.id,
            draft_id=parent.id,
            topic=parent.topic,
            draft=current,
            sources=sources,
            publish_score=parent.publish_score,
        )
        feedback_metadata = _feedback_metadata(
            feedback=feedback,
            model=settings.blog_feedback_model,
            parent_draft_id=parent.id,
            additional_instructions=additional_instructions,
        )
        update_draft_feedback_metadata(db, draft_id=parent.id, feedback_metadata=feedback_metadata)

        regenerated = await regenerate_article_draft(
            settings=settings,
            db=db,
            run_id=run.id,
            parent_draft_id=parent.id,
            topic=parent.topic,
            sources=sources,
            current_draft=current,
            feedback=feedback,
            additional_instructions=additional_instructions,
        )
        regenerated = _sanitize_draft(regenerated)

        claims = await extract_claims(
            settings=settings,
            db=db,
            run_id=run.id,
            topic_id=parent.topic_id,
            draft=regenerated,
        )
        verifications = await verify_claims(
            settings=settings,
            db=db,
            run_id=run.id,
            topic_id=parent.topic_id,
            draft_id=None,
            sources=sources,
            claims=claims,
        )
        polished = await polish_brand_draft(
            settings=settings,
            db=db,
            run_id=run.id,
            topic_id=parent.topic_id,
            draft_id=None,
            draft=regenerated,
            verifications=verifications,
        )
        polished = _sanitize_draft(polished)

        new_draft = create_draft_revision(
            db,
            parent_draft=parent,
            draft_output=polished,
            feedback_metadata=feedback_metadata,
        )
        create_fact_checks_from_verifications(db, draft_id=new_draft.id, verifications=verifications)

        deterministic_checks = run_deterministic_publish_checks(
            settings=settings,
            title=polished.title,
            slug=new_draft.slug,
            meta_description=polished.meta_description,
            markdown_content=polished.markdown_content,
            verifications=verifications,
        )
        safety = await run_publish_safety_for_draft(
            settings=settings,
            db=db,
            draft_id=new_draft.id,
            run_id=run.id,
        )
        if deterministic_checks.blockers:
            update_publish_metadata(
                db,
                draft_id=new_draft.id,
                publish_score=safety.publish_score,
                publish_ready=safety.publish_ready,
                status=DraftStatus.NEEDS_REVIEW,
            )

        mark_run_completed(
            db,
            run.id,
            {
                "parent_draft_id": str(parent.id),
                "draft_id": str(new_draft.id),
                "topic_id": str(parent.topic_id),
                "task": "draft_regeneration",
            },
        )
        return DraftRegenerationResult(
            parent_draft_id=parent.id,
            draft_id=new_draft.id,
            topic_id=parent.topic_id,
            version=new_draft.version,
            feedback=feedback,
            publish_ready=safety.publish_ready,
            publish_score=safety.publish_score,
        )
    except Exception as exc:
        mark_run_failed(db, run.id, str(exc))
        raise


def read_feedback_metadata(draft: BlogDraft) -> dict[str, Any] | None:
    metadata = (draft.seo_json or {}).get("latest_feedback")
    if not isinstance(metadata, dict):
        metadata = (draft.seo_json or {}).get("regeneration")
    return metadata if isinstance(metadata, dict) else None


def _require_draft(db: Session, draft_id: UUID) -> BlogDraft:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise ValueError("Draft not found")
    return draft


def _sources_for_draft(db: Session, draft: BlogDraft) -> list[Source]:
    sources = list_sources_by_draft(db, draft.id)
    if sources:
        return sources
    return list_sources_by_topic(db, draft.topic_id)


def _draft_output(draft: BlogDraft) -> BlogDraftOutput:
    return _sanitize_draft(
        BlogDraftOutput(
            title=draft.title,
            slug=draft.slug,
            meta_title=draft.meta_title or draft.title,
            meta_description=draft.meta_description or "",
            markdown_content=draft.markdown_content,
            notes="Existing saved draft.",
        )
    )


def _sanitize_draft(draft: BlogDraftOutput) -> BlogDraftOutput:
    return draft.model_copy(
        update={
            "title": _replace_em_dash(draft.title),
            "meta_title": _replace_em_dash(draft.meta_title),
            "meta_description": _replace_em_dash(draft.meta_description),
            "markdown_content": _replace_em_dash(draft.markdown_content),
            "notes": _replace_em_dash(draft.notes),
        }
    )


def _replace_em_dash(value: str) -> str:
    return value.replace("—", " - ")


def _feedback_metadata(
    *,
    feedback: DraftFeedbackOutput,
    model: str,
    parent_draft_id: UUID,
    additional_instructions: str | None,
) -> dict[str, object]:
    return {
        "feedback": feedback.model_dump(mode="json"),
        "model": model,
        "created_from_draft_id": str(parent_draft_id),
        "additional_instructions": additional_instructions,
        "created_at": datetime.now(UTC).isoformat(),
    }
