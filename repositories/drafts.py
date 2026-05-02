from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BlogDraft
from schemas.common import DraftStatus
from schemas.workflow import BlogDraftOutput, OutlineOutput, SEOAnglesOutput


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


def create_generated_draft(
    db: Session,
    *,
    topic_id: UUID,
    draft_output: BlogDraftOutput,
    outline: OutlineOutput,
    seo_angles: SEOAnglesOutput,
    target_keyword: str | None,
    version: int | None = None,
    seo_metadata: dict[str, object] | None = None,
) -> BlogDraft:
    base_slug = _slugify(draft_output.slug or outline.slug or draft_output.title)
    seo_json: dict[str, object] = seo_angles.model_dump(mode="json")
    if seo_metadata:
        seo_json = {**seo_json, **seo_metadata}
    values: dict[str, object] = {}
    if version is not None:
        values["version"] = version
    draft = BlogDraft(
        topic_id=topic_id,
        title=draft_output.title,
        slug=_unique_slug(db, base_slug),
        meta_title=draft_output.meta_title,
        meta_description=draft_output.meta_description,
        target_keyword=target_keyword,
        markdown_content=draft_output.markdown_content,
        outline_json=outline.model_dump(mode="json"),
        seo_json=seo_json,
        status=DraftStatus.DRAFT.value,
        publish_ready=False,
        **values,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def create_draft_revision(
    db: Session,
    *,
    parent_draft: BlogDraft,
    draft_output: BlogDraftOutput,
    feedback_metadata: dict[str, object],
) -> BlogDraft:
    base_slug = _slugify(draft_output.slug or parent_draft.slug or draft_output.title)
    draft = BlogDraft(
        topic_id=parent_draft.topic_id,
        title=draft_output.title,
        slug=_unique_slug(db, base_slug),
        meta_title=draft_output.meta_title,
        meta_description=draft_output.meta_description,
        target_keyword=parent_draft.target_keyword,
        markdown_content=draft_output.markdown_content,
        outline_json=parent_draft.outline_json,
        seo_json={
            **(parent_draft.seo_json or {}),
            "regeneration": feedback_metadata,
        },
        status=DraftStatus.DRAFT.value,
        version=next_draft_version(db, parent_draft.topic_id),
        publish_ready=False,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def next_draft_version(db: Session, topic_id: UUID) -> int:
    if not hasattr(db, "scalar"):
        return 1
    max_version = db.scalar(select(func.max(BlogDraft.version)).where(BlogDraft.topic_id == topic_id))
    return int(max_version or 0) + 1


def update_draft_feedback_metadata(
    db: Session,
    *,
    draft_id: UUID,
    feedback_metadata: dict[str, object],
) -> BlogDraft | None:
    draft = get_draft(db, draft_id)
    if draft is None:
        return None

    draft.seo_json = {
        **(draft.seo_json or {}),
        "latest_feedback": feedback_metadata,
    }
    db.commit()
    db.refresh(draft)
    return draft


def update_publish_metadata(
    db: Session,
    *,
    draft_id: UUID,
    publish_score: int | None,
    publish_ready: bool,
    status: DraftStatus | None = None,
) -> BlogDraft | None:
    draft = get_draft(db, draft_id)
    if draft is None:
        return None

    draft.publish_score = publish_score
    draft.publish_ready = publish_ready
    if status is not None:
        draft.status = status.value
    db.commit()
    db.refresh(draft)
    return draft


def update_safety_metadata(
    db: Session,
    *,
    draft_id: UUID,
    safety_metadata: dict[str, object],
) -> BlogDraft | None:
    draft = get_draft(db, draft_id)
    if draft is None:
        return None

    draft.seo_json = {
        **(draft.seo_json or {}),
        "publish_safety": safety_metadata,
    }
    db.commit()
    db.refresh(draft)
    return draft


def _unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug or "draft"
    existing_slugs = set(
        db.scalars(select(BlogDraft.slug).where(BlogDraft.slug.like(f"{slug}%"))).all()
    )
    if slug not in existing_slugs:
        return slug

    suffix = 2
    while f"{slug}-{suffix}" in existing_slugs:
        suffix += 1
    return f"{slug}-{suffix}"


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in normalized.split("-") if part)[:255]
