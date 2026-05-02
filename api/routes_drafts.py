from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_database_session
from app.errors import not_found
from repositories.drafts import get_draft, list_drafts as list_drafts_repo, update_draft_status
from repositories.fact_checks import list_fact_checks_by_draft
from schemas.common import DraftStatus
from schemas.draft import DraftFeedbackRead, DraftRead
from schemas.workflow import DraftFeedbackOutput, DraftRegenerateRequest, DraftRegenerationResult, DraftSafetyReport
from services.draft_regeneration import (
    generate_feedback_for_draft,
    read_feedback_metadata,
    regenerate_draft_with_feedback,
)
from services.publish_safety import build_safety_report, run_publish_safety_for_draft

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("", response_model=list[DraftRead])
def list_drafts(
    db: Session = Depends(get_database_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[DraftRead]:
    drafts = list_drafts_repo(db, limit=limit)
    return [DraftRead.model_validate(draft) for draft in drafts]


@router.get("/{draft_id}", response_model=DraftRead)
def read_draft(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftRead:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise not_found("Draft not found")
    return DraftRead.model_validate(draft)


@router.post("/{draft_id}/approve", response_model=DraftRead)
def approve_draft(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftRead:
    draft = update_draft_status(db, draft_id, DraftStatus.APPROVED)
    if draft is None:
        raise not_found("Draft not found")
    return DraftRead.model_validate(draft)


@router.get("/{draft_id}/feedback", response_model=DraftFeedbackRead)
def read_draft_feedback(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftFeedbackRead:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise not_found("Draft not found")

    metadata = read_feedback_metadata(draft)
    feedback = None
    if metadata and isinstance(metadata.get("feedback"), dict):
        feedback = DraftFeedbackOutput.model_validate(metadata["feedback"])

    created_from_draft_id = None
    if metadata and metadata.get("created_from_draft_id"):
        created_from_draft_id = UUID(str(metadata["created_from_draft_id"]))

    return DraftFeedbackRead(
        draft_id=draft.id,
        feedback=feedback,
        model=str(metadata.get("model")) if metadata and metadata.get("model") is not None else None,
        created_from_draft_id=created_from_draft_id,
        additional_instructions=(
            str(metadata.get("additional_instructions"))
            if metadata and metadata.get("additional_instructions") is not None
            else None
        ),
    )


@router.post("/{draft_id}/feedback", response_model=DraftFeedbackRead)
async def create_draft_feedback(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftFeedbackRead:
    try:
        feedback = await generate_feedback_for_draft(
            settings=get_settings(),
            db=db,
            draft_id=draft_id,
        )
    except ValueError as exc:
        raise not_found(str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Draft feedback failed: {exc}",
        ) from exc

    return DraftFeedbackRead(
        draft_id=draft_id,
        feedback=feedback,
        model=get_settings().blog_feedback_model,
        created_from_draft_id=draft_id,
        additional_instructions=None,
    )


@router.post("/{draft_id}/regenerate", response_model=DraftRegenerationResult)
async def regenerate_draft(
    draft_id: UUID,
    payload: DraftRegenerateRequest,
    db: Session = Depends(get_database_session),
) -> DraftRegenerationResult:
    try:
        return await regenerate_draft_with_feedback(
            settings=get_settings(),
            db=db,
            draft_id=draft_id,
            additional_instructions=payload.additional_instructions,
        )
    except ValueError as exc:
        raise not_found(str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Draft regeneration failed: {exc}",
        ) from exc


@router.post("/{draft_id}/publish-judgment", response_model=DraftSafetyReport)
async def rerun_publish_judgment(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftSafetyReport:
    try:
        return await run_publish_safety_for_draft(
            settings=get_settings(),
            db=db,
            draft_id=draft_id,
        )
    except ValueError as exc:
        raise not_found(str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Publish judgment failed: {exc}",
        ) from exc


@router.get("/{draft_id}/safety-report", response_model=DraftSafetyReport)
def read_safety_report(
    draft_id: UUID,
    db: Session = Depends(get_database_session),
) -> DraftSafetyReport:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise not_found("Draft not found")

    return build_safety_report(
        draft=draft,
        fact_checks=list_fact_checks_by_draft(db, draft_id),
    )
