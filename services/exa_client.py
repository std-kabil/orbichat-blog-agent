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

EXA_SEARCH_URL = "https://api.exa.ai/search"


class ExaSearchClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        if not settings.exa_api_key:
            raise ServiceConfigurationError("EXA_API_KEY is required for Exa search")
        self._api_key = settings.exa_api_key
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
            response = await self._post(query=query, max_results=max_results)
            payload = require_mapping(response.json(), SearchProvider.EXA.value)
            results = _normalize_exa_results(payload)
            record_search_call(
                db,
                provider=SearchProvider.EXA.value,
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
                provider=SearchProvider.EXA.value,
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
    async def _post(self, *, query: str, max_results: int) -> httpx.Response:
        body = {
            "query": query,
            "numResults": max_results,
            "contents": {"text": True},
        }
        headers = {"x-api-key": self._api_key}
        if self._http_client is not None:
            response = await self._http_client.post(
                EXA_SEARCH_URL,
                json=body,
                headers=headers,
                timeout=30,
            )
            raise_for_status(response)
            return response

        async with httpx.AsyncClient() as client:
            response = await client.post(EXA_SEARCH_URL, json=body, headers=headers, timeout=30)
            raise_for_status(response)
            return response


def _normalize_exa_results(payload: dict[str, object]) -> list[NormalizedSearchResult]:
    raw_results = payload.get("results", [])
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
        snippet = item.get("text") or item.get("summary") or item.get("snippet") or ""
        results.append(
            NormalizedSearchResult(
                title=title,
                url=url,
                snippet=str(snippet),
                published_at=parse_datetime(item.get("publishedDate")),
                source_provider=SearchProvider.EXA,
                raw=item,
            )
        )
    return results
