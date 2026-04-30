from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from schemas.common import APIModel, SearchProvider

SearchIntent = Literal["informational", "commercial", "navigational", "comparison", "tutorial"]


class TrendCandidateCreate(APIModel):
    run_id: UUID
    title: str
    query: str
    source: SearchProvider
    url: str | None = None
    snippet: str | None = None
    detected_at: datetime
    raw_score: Decimal | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TrendCandidateRead(TrendCandidateCreate):
    id: UUID
    created_at: datetime


class TopicCandidateInput(APIModel):
    seed_query: str
    candidate_titles: list[str]
    snippets: list[str]
    source_urls: list[str]


class TopicScoreOutput(APIModel):
    title: str
    target_keyword: str
    search_intent: SearchIntent
    trend_score: int = Field(ge=0, le=100)
    orbichat_relevance_score: int = Field(ge=0, le=100)
    seo_score: int = Field(ge=0, le=100)
    conversion_score: int = Field(ge=0, le=100)
    total_score: int = Field(ge=0, le=100)
    recommended: bool
    reasoning: str
    cta_angle: str


class DailyTrendScanResult(APIModel):
    run_id: UUID
    candidate_count: int
    deduped_candidate_count: int
    topic_count: int
    provider_warnings: list[str]
    skipped_providers: list[str]
