from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_database_session
from app.errors import not_found
from repositories.drafts import get_draft, list_drafts as list_drafts_repo
from repositories.fact_checks import list_fact_checks_by_draft
from schemas.draft import DraftRead
from schemas.workflow import DraftSafetyReport
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
