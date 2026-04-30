from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from repositories.trend_candidates import create_trend_candidates
from schemas.common import SearchProvider
from schemas.search import NormalizedSearchResult, SearchProviderWarning, SearchRouterResult
from schemas.trend import TopicCandidateInput, TrendCandidateCreate
from services.errors import ServiceConfigurationError
from services.search_provider_config import enabled_search_providers
from services.search_router import SearchRouter

SEED_QUERIES: tuple[str, ...] = (
    "AI chat apps",
    "ChatGPT alternatives",
    "Claude vs GPT",
    "Gemini vs Claude",
    "Grok vs ChatGPT",
    "best AI model for coding",
    "best AI model for students",
    "best AI model for writing",
    "AI productivity tools",
    "OpenRouter models",
    "new AI model releases",
    "AI coding assistants",
    "AI search tools",
    "multi-model AI chat",
)

ALL_SEARCH_PROVIDERS: tuple[SearchProvider, ...] = (
    SearchProvider.TAVILY,
    SearchProvider.EXA,
    SearchProvider.BRAVE,
)

MAX_RESULTS_PER_PROVIDER = 5
MAX_TOPIC_GROUPS = 8
MAX_CANDIDATES_PER_TOPIC_INPUT = 6

_STOPWORDS = {
    "a",
    "ai",
    "an",
    "and",
    "apps",
    "best",
    "for",
    "in",
    "model",
    "models",
    "new",
    "of",
    "the",
    "to",
    "tools",
    "vs",
    "with",
}


class TrendSearchRouter(Protocol):
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


async def discover_trend_candidates(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    search_router: TrendSearchRouter | None = None,
    seed_queries: Sequence[str] = SEED_QUERIES,
) -> tuple[list[TrendCandidateCreate], list[SearchProviderWarning], list[SearchProvider]]:
    enabled_providers = enabled_search_providers(settings)
    if not enabled_providers:
        raise ServiceConfigurationError("At least one search provider API key is required for daily trend scan")

    router = search_router or SearchRouter(settings)
    candidates: list[TrendCandidateCreate] = []
    warnings: list[SearchProviderWarning] = []

    for query in seed_queries:
        search_result = await router.search(
            query=query,
            max_results_per_provider=MAX_RESULTS_PER_PROVIDER,
            db=db,
            run_id=run_id,
        )
        warnings.extend(search_result.warnings)
        candidates.extend(_candidate_from_search_result(run_id, query, result) for result in search_result.results)

    create_trend_candidates(db, candidates)

    skipped_providers = [provider for provider in ALL_SEARCH_PROVIDERS if provider not in enabled_providers]
    return candidates, _unique_warnings(warnings), skipped_providers


def dedupe_trend_candidates(candidates: Sequence[TrendCandidateCreate]) -> list[TrendCandidateCreate]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    deduped: list[TrendCandidateCreate] = []

    for candidate in candidates:
        normalized_url = _normalize_url(candidate.url) if candidate.url else None
        normalized_title = _normalize_text(candidate.title)
        if normalized_url is not None and normalized_url in seen_urls:
            continue
        if normalized_title in seen_titles:
            continue
        if normalized_url is not None:
            seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        deduped.append(candidate)

    return deduped


def group_topic_candidates(candidates: Sequence[TrendCandidateCreate]) -> list[TopicCandidateInput]:
    grouped: dict[str, list[TrendCandidateCreate]] = defaultdict(list)
    for candidate in candidates:
        grouped[_topic_group_key(candidate)].append(candidate)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (len(item[1]), _group_snippet_length(item[1])),
        reverse=True,
    )

    topic_inputs: list[TopicCandidateInput] = []
    for seed_query, group_candidates in ranked_groups[:MAX_TOPIC_GROUPS]:
        selected = group_candidates[:MAX_CANDIDATES_PER_TOPIC_INPUT]
        topic_inputs.append(
            TopicCandidateInput(
                seed_query=seed_query,
                candidate_titles=[candidate.title for candidate in selected],
                snippets=[candidate.snippet or "" for candidate in selected if candidate.snippet],
                source_urls=[candidate.url for candidate in selected if candidate.url],
            )
        )

    return topic_inputs


def _candidate_from_search_result(
    run_id: UUID,
    query: str,
    result: NormalizedSearchResult,
) -> TrendCandidateCreate:
    return TrendCandidateCreate(
        run_id=run_id,
        title=result.title,
        query=query,
        source=result.source_provider,
        url=result.url,
        snippet=result.snippet,
        detected_at=result.published_at or datetime.now(UTC),
        metadata_json={"raw": result.raw},
    )


def _unique_warnings(warnings: Iterable[SearchProviderWarning]) -> list[SearchProviderWarning]:
    seen: set[tuple[SearchProvider, str]] = set()
    unique_warnings: list[SearchProviderWarning] = []
    for warning in warnings:
        key = (warning.provider, warning.message)
        if key in seen:
            continue
        seen.add(key)
        unique_warnings.append(warning)
    return unique_warnings


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query_params, doseq=True),
            "",
        )
    )


def _topic_group_key(candidate: TrendCandidateCreate) -> str:
    query = candidate.query.strip()
    title_terms = _significant_terms(candidate.title)
    query_terms = _significant_terms(query)
    shared_terms = title_terms.intersection(query_terms)
    if shared_terms:
        return query
    return " ".join(sorted(title_terms)[:3]) or query


def _significant_terms(value: str) -> set[str]:
    normalized = _normalize_text(value)
    return {term for term in normalized.split() if len(term) > 2 and term not in _STOPWORDS}


def _normalize_text(value: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


def _group_snippet_length(candidates: Sequence[TrendCandidateCreate]) -> int:
    return sum(len(candidate.snippet or "") for candidate in candidates)
