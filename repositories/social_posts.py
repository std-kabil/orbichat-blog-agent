from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import SocialPost
from schemas.workflow import SocialPostDraft


def create_draft_social_posts(
    db: Session,
    *,
    draft_id: UUID,
    posts: Iterable[SocialPostDraft],
) -> list[SocialPost]:
    social_posts = [
        SocialPost(
            draft_id=draft_id,
            platform=post.platform,
            content=post.content,
            status="draft",
            metadata_json=post.metadata,
        )
        for post in posts
    ]
    db.add_all(social_posts)
    db.commit()
    for post in social_posts:
        db.refresh(post)
    return social_posts
