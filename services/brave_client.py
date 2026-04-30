from time import perf_counter
from uuid import UUID

import httpx
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import Settings
from schemas.common import SearchProvider
from schemas.search import NormalizedSearchResult
from services.cost_tracker import elapsed_ms, record_search_call
from services.errors import ServiceConfigurationError
from services.search_utils import parse_datetime, raise_for_status, require_mapping, transient_http_error

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        if not settings.brave_api_key:
            raise ServiceConfigurationError("BRAVE_API_KEY is required for Brave search")
        self._api_key = settings.brave_api_key
        self._http_client = http_client

    async def search(
        self,
        *,
        query: str,
        max_results: int = 10,
        db: Session | None = None,
        run_id: UUID | None = None,
        topic_id: UUID | None = None,
        draft_id: UUID | None = None,
    ) -> list[NormalizedSearchResult]:
        started_at = perf_counter()
        try:
            response = await self._get(query=query, max_results=max_results)
            payload = require_mapping(response.json(), SearchProvider.BRAVE.value)
            results = _normalize_brave_results(payload)
            record_search_call(
                db,
                provider=SearchProvider.BRAVE.value,
                query=query,
                run_id=run_id,
                topic_id=topic_id,
                draft_id=draft_id,
                result_count=len(results),
                latency_ms=elapsed_ms(started_at),
            )
            return results
        except Exception as exc:
            record_search_call(
                db,
                provider=SearchProvider.BRAVE.value,
                query=query,
                run_id=run_id,
                topic_id=topic_id,
                draft_id=draft_id,
                result_count=0,
                latency_ms=elapsed_ms(started_at),
                success=False,
                error=str(exc),
            )
            raise

    @retry(
        retry=retry_if_exception(transient_http_error),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, *, query: str, max_results: int) -> httpx.Response:
        headers = {"X-Subscription-Token": self._api_key}
        params: dict[str, str | int] = {"q": query, "count": max_results}
        if self._http_client is not None:
            response = await self._http_client.get(
                BRAVE_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            raise_for_status(response)
            return response

        async with httpx.AsyncClient() as client:
            response = await client.get(BRAVE_SEARCH_URL, params=params, headers=headers, timeout=30)
            raise_for_status(response)
            return response


def _normalize_brave_results(payload: dict[str, object]) -> list[NormalizedSearchResult]:
    web = payload.get("web", {})
    raw_results: object = web.get("results", []) if isinstance(web, dict) else []
    if not isinstance(raw_results, list):
        return []

    results: list[NormalizedSearchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        if not title or not url:
            continue
        results.append(
            NormalizedSearchResult(
                title=title,
                url=url,
                snippet=str(item.get("description") or ""),
                published_at=parse_datetime(item.get("age")),
                source_provider=SearchProvider.BRAVE,
                raw=item,
            )
        )
    return results
