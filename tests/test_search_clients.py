from typing import cast

import httpx
import pytest

from app.config import Settings
from schemas.common import SearchProvider
from schemas.search import NormalizedSearchResult
from services.brave_client import BraveSearchClient
from services.exa_client import ExaSearchClient
from services.search_router import SearchRouter
from services.tavily_client import TavilySearchClient


def _async_client(payload: dict[str, object], status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload, request=request)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_tavily_search_normalizes_results() -> None:
    async with _async_client(
        {
            "results": [
                {
                    "title": "Tavily result",
                    "url": "https://example.com/tavily",
                    "content": "Snippet",
                    "published_date": "2026-04-30T00:00:00Z",
                }
            ]
        }
    ) as http_client:
        results = await TavilySearchClient(
            Settings(tavily_api_key="key"),
            http_client=http_client,
        ).search(query="ai")

    assert results[0].source_provider == SearchProvider.TAVILY
    assert results[0].title == "Tavily result"


@pytest.mark.anyio
async def test_exa_search_normalizes_results() -> None:
    async with _async_client(
        {
            "results": [
                {
                    "title": "Exa result",
                    "url": "https://example.com/exa",
                    "text": "Snippet",
                    "publishedDate": "2026-04-30T00:00:00Z",
                }
            ]
        }
    ) as http_client:
        results = await ExaSearchClient(
            Settings(exa_api_key="key"),
            http_client=http_client,
        ).search(query="ai")

    assert results[0].source_provider == SearchProvider.EXA
    assert results[0].url == "https://example.com/exa"


@pytest.mark.anyio
async def test_brave_search_normalizes_results() -> None:
    async with _async_client(
        {
            "web": {
                "results": [
                    {
                        "title": "Brave result",
                        "url": "https://example.com/brave",
                        "description": "Snippet",
                    }
                ]
            }
        }
    ) as http_client:
        results = await BraveSearchClient(
            Settings(brave_api_key="key"),
            http_client=http_client,
        ).search(query="ai")

    assert results[0].source_provider == SearchProvider.BRAVE
    assert results[0].snippet == "Snippet"


class FakeSearchClient:
    def __init__(
        self,
        provider: SearchProvider,
        *,
        should_fail: bool = False,
    ) -> None:
        self.provider = provider
        self.should_fail = should_fail

    async def search(
        self,
        *,
        query: str,
        max_results: int = 10,
        db: object | None = None,
        run_id: object | None = None,
        topic_id: object | None = None,
        draft_id: object | None = None,
    ) -> list[NormalizedSearchResult]:
        if self.should_fail:
            raise RuntimeError(f"{self.provider.value} failed")
        return [
            NormalizedSearchResult(
                title=f"{self.provider.value} result",
                url=f"https://example.com/{self.provider.value}",
                snippet="Snippet",
                source_provider=self.provider,
                raw={},
            )
        ]


@pytest.mark.anyio
async def test_search_router_skips_brave_without_api_key() -> None:
    router = SearchRouter(
        Settings(tavily_api_key="tavily", exa_api_key="exa", brave_api_key=None),
        tavily_client=cast(TavilySearchClient, FakeSearchClient(SearchProvider.TAVILY)),
        exa_client=cast(ExaSearchClient, FakeSearchClient(SearchProvider.EXA)),
        brave_client=cast(BraveSearchClient, FakeSearchClient(SearchProvider.BRAVE)),
    )

    result = await router.search(query="ai")

    assert [item.source_provider for item in result.results] == [
        SearchProvider.TAVILY,
        SearchProvider.EXA,
    ]
    assert result.warnings == []


@pytest.mark.anyio
async def test_search_router_returns_warnings_for_provider_failure() -> None:
    router = SearchRouter(
        Settings(tavily_api_key="tavily", exa_api_key="exa"),
        tavily_client=cast(TavilySearchClient, FakeSearchClient(SearchProvider.TAVILY)),
        exa_client=cast(ExaSearchClient, FakeSearchClient(SearchProvider.EXA, should_fail=True)),
    )

    result = await router.search(query="ai")

    assert [item.source_provider for item in result.results] == [SearchProvider.TAVILY]
    assert result.warnings[0].provider == SearchProvider.EXA
