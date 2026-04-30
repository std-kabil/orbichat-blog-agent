from app.config import Settings
from services.search_provider_config import SearchProvider, enabled_search_providers


def test_brave_search_is_disabled_without_api_key() -> None:
    settings = Settings(
        tavily_api_key="tavily-key",
        exa_api_key="exa-key",
        brave_api_key=None,
    )

    assert enabled_search_providers(settings) == (
        SearchProvider.TAVILY,
        SearchProvider.EXA,
    )


def test_brave_search_is_enabled_when_api_key_is_present() -> None:
    settings = Settings(
        tavily_api_key="tavily-key",
        exa_api_key="exa-key",
        brave_api_key="brave-key",
    )

    assert enabled_search_providers(settings) == (
        SearchProvider.TAVILY,
        SearchProvider.EXA,
        SearchProvider.BRAVE,
    )
