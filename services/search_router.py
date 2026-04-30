from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from schemas.common import SearchProvider
from schemas.search import NormalizedSearchResult, SearchProviderWarning, SearchRouterResult
from services.budget import assert_budget_available
from services.brave_client import BraveSearchClient
from services.cost_tracker import record_search_call
from services.errors import BudgetExceededError
from services.exa_client import ExaSearchClient
from services.pricing import calculate_search_cost
from services.search_provider_config import enabled_search_providers
from services.tavily_client import TavilySearchClient


class SearchRouter:
    def __init__(
        self,
        settings: Settings,
        *,
        tavily_client: TavilySearchClient | None = None,
        exa_client: ExaSearchClient | None = None,
        brave_client: BraveSearchClient | None = None,
    ) -> None:
        self._settings = settings
        self._tavily_client = tavily_client
        self._exa_client = exa_client
        self._brave_client = brave_client

    async def search(
        self,
        *,
        query: str,
        max_results_per_provider: int = 10,
        db: Session | None = None,
        run_id: UUID | None = None,
        topic_id: UUID | None = None,
        draft_id: UUID | None = None,
    ) -> SearchRouterResult:
        results: list[NormalizedSearchResult] = []
        warnings: list[SearchProviderWarning] = []

        for provider in enabled_search_providers(self._settings):
            try:
                assert_budget_available(
                    settings=self._settings,
                    db=db,
                    estimated_cost_usd=calculate_search_cost(
                        settings=self._settings,
                        provider=provider.value,
                    ),
                    run_id=run_id,
                    task_name="search",
                    provider=provider.value,
                )
                provider_results = await self._search_provider(
                    provider=provider,
                    query=query,
                    max_results=max_results_per_provider,
                    db=db,
                    run_id=run_id,
                    topic_id=topic_id,
                    draft_id=draft_id,
                )
                results.extend(provider_results)
            except Exception as exc:
                if isinstance(exc, BudgetExceededError):
                    record_search_call(
                        db,
                        provider=provider.value,
                        query=query,
                        result_count=0,
                        latency_ms=None,
                        settings=self._settings,
                        run_id=run_id,
                        topic_id=topic_id,
                        draft_id=draft_id,
                        success=False,
                        error=str(exc),
                    )
                warnings.append(
                    SearchProviderWarning(
                        provider=provider,
                        message=str(exc),
                    )
                )

        return SearchRouterResult(results=results, warnings=warnings)

    async def _search_provider(
        self,
        *,
        provider: SearchProvider,
        query: str,
        max_results: int,
        db: Session | None,
        run_id: UUID | None,
        topic_id: UUID | None,
        draft_id: UUID | None,
    ) -> list[NormalizedSearchResult]:
        if provider is SearchProvider.TAVILY:
            tavily_client = self._tavily_client or TavilySearchClient(self._settings)
            return await tavily_client.search(
                query=query,
                max_results=max_results,
                db=db,
                run_id=run_id,
                topic_id=topic_id,
                draft_id=draft_id,
            )

        if provider is SearchProvider.EXA:
            exa_client = self._exa_client or ExaSearchClient(self._settings)
            return await exa_client.search(
                query=query,
                max_results=max_results,
                db=db,
                run_id=run_id,
                topic_id=topic_id,
                draft_id=draft_id,
            )

        brave_client = self._brave_client or BraveSearchClient(self._settings)
        return await brave_client.search(
            query=query,
            max_results=max_results,
            db=db,
            run_id=run_id,
            topic_id=topic_id,
            draft_id=draft_id,
        )
