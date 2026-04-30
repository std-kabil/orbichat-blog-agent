from datetime import datetime
from typing import Any

from schemas.common import APIModel, SearchProvider


class NormalizedSearchResult(APIModel):
    title: str
    url: str
    snippet: str
    published_at: datetime | None = None
    source_provider: SearchProvider
    raw: dict[str, Any]


class SearchProviderWarning(APIModel):
    provider: SearchProvider
    message: str


class SearchRouterResult(APIModel):
    results: list[NormalizedSearchResult]
    warnings: list[SearchProviderWarning]
