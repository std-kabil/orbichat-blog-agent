from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.errors import not_found
from repositories.drafts import get_draft, list_drafts as list_drafts_repo
from schemas.draft import DraftRead

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
