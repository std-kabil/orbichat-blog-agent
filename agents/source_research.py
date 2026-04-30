from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Source, Topic
from repositories.sources import create_sources_from_search_results
from schemas.search import NormalizedSearchResult, SearchProviderWarning, SearchRouterResult
from services.search_provider_config import enabled_search_providers
from services.search_router import SearchRouter

MAX_SOURCE_RESULTS_PER_PROVIDER = 4


class SourceSearchRouter(Protocol):
    async def search(
        self,
        *,
        query: str,
        max_results_per_provider: int = 10,
        db: Session | None = None,
        run_id: UUID | None = None,
        topic_id: UUID | None = None,
        draft_id: UUID | None = None,
    ) -> SearchRouterResult: ...


async def research_sources_for_topic(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic: Topic,
    search_router: SourceSearchRouter | None = None,
) -> tuple[list[Source], list[SearchProviderWarning]]:
    if not enabled_search_providers(settings):
        raise RuntimeError("At least one search provider API key is required for source research")

    router = search_router or SearchRouter(settings)
    all_results: list[NormalizedSearchResult] = []
    warnings: list[SearchProviderWarning] = []

    for query in build_source_queries(topic):
        result = await router.search(
            query=query,
            max_results_per_provider=MAX_SOURCE_RESULTS_PER_PROVIDER,
            db=db,
            run_id=run_id,
            topic_id=topic.id,
        )
        all_results.extend(result.results)
        warnings.extend(result.warnings)

    deduped_results = _dedupe_results(all_results)
    if not deduped_results:
        warning_text = "; ".join(f"{warning.provider.value}: {warning.message}" for warning in warnings)
        raise RuntimeError(f"Source research found no usable sources. {warning_text}".strip())

    return (
        create_sources_from_search_results(db, topic_id=topic.id, results=deduped_results),
        _unique_warnings(warnings),
    )


def build_source_queries(topic: Topic) -> list[str]:
    parts = [topic.title]
    if topic.target_keyword:
        parts.append(topic.target_keyword)
    if topic.search_intent:
        parts.append(topic.search_intent)

    base_query = " ".join(part for part in parts if part).strip()
    return [
        base_query,
        f"{base_query} sources data examples",
        f"{base_query} 2026 AI tools comparison",
    ]


def _dedupe_results(results: Sequence[NormalizedSearchResult]) -> list[NormalizedSearchResult]:
    seen: set[str] = set()
    deduped: list[NormalizedSearchResult] = []
    for result in results:
        key = result.url.strip().lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def _unique_warnings(warnings: Sequence[SearchProviderWarning]) -> list[SearchProviderWarning]:
    seen: set[tuple[str, str]] = set()
    unique: list[SearchProviderWarning] = []
    for warning in warnings:
        key = (warning.provider.value, warning.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(warning)
    return unique
