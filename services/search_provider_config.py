from app.config import Settings
from schemas.common import SearchProvider

__all__ = ["SearchProvider", "enabled_search_providers"]


def enabled_search_providers(settings: Settings) -> tuple[SearchProvider, ...]:
    providers: list[SearchProvider] = []

    if settings.tavily_api_key:
        providers.append(SearchProvider.TAVILY)

    if settings.exa_api_key:
        providers.append(SearchProvider.EXA)

    if settings.brave_api_key:
        providers.append(SearchProvider.BRAVE)

    return tuple(providers)
