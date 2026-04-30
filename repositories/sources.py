from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Source
from schemas.search import NormalizedSearchResult


def create_sources_from_search_results(
    db: Session,
    *,
    topic_id: UUID,
    results: Iterable[NormalizedSearchResult],
) -> list[Source]:
    sources: list[Source] = []
    seen_urls: set[str] = set()
    for result in results:
        if result.url in seen_urls:
            continue
        seen_urls.add(result.url)
        sources.append(
            Source(
                topic_id=topic_id,
                url=result.url,
                title=result.title,
                published_at=result.published_at,
                snippet=result.snippet,
                source_type=result.source_provider.value,
                metadata_json={"raw": result.raw, "source_provider": result.source_provider.value},
            )
        )

    db.add_all(sources)
    db.commit()
    for source in sources:
        db.refresh(source)
    return sources


def list_sources_by_topic(db: Session, topic_id: UUID) -> list[Source]:
    statement = select(Source).where(Source.topic_id == topic_id).order_by(Source.created_at.asc())
    return list(db.scalars(statement).all())


def list_sources_by_draft(db: Session, draft_id: UUID) -> list[Source]:
    statement = select(Source).where(Source.draft_id == draft_id).order_by(Source.created_at.asc())
    return list(db.scalars(statement).all())


def attach_sources_to_draft(db: Session, *, source_ids: Iterable[UUID], draft_id: UUID) -> int:
    sources = list(db.scalars(select(Source).where(Source.id.in_(list(source_ids)))).all())
    for source in sources:
        source.draft_id = draft_id
        source.used_in_article = True
    db.commit()
    return len(sources)
