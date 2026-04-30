from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BlogDraft
from schemas.common import DraftStatus


def list_drafts(db: Session, limit: int = 50) -> list[BlogDraft]:
    statement = select(BlogDraft).order_by(BlogDraft.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_draft(db: Session, draft_id: UUID) -> BlogDraft | None:
    return db.get(BlogDraft, draft_id)


def update_draft_status(db: Session, draft_id: UUID, status: DraftStatus) -> BlogDraft | None:
    draft = get_draft(db, draft_id)
    if draft is None:
        return None

    draft.status = status.value
    db.commit()
    db.refresh(draft)
    return draft
