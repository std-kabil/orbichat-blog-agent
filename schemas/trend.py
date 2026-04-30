from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def normalize_provider_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        _copy_first_present(
            normalized,
            "title",
            ("topic_title", "topic", "headline", "recommended_title", "suggested_title"),
        )
        _copy_first_present(
            normalized,
            "target_keyword",
            ("keyword", "primary_keyword", "seed_query", "search_keyword"),
        )
        _copy_first_present(
            normalized,
            "search_intent",
            ("intent", "user_intent"),
        )
        _copy_first_present(
            normalized,
            "trend_score",
            ("trendiness_score", "freshness_score", "demand_score"),
        )
        _copy_first_present(
            normalized,
            "orbichat_relevance_score",
            ("orbichat_fit_score", "relevance_score", "product_fit_score"),
        )
        _copy_first_present(
            normalized,
            "seo_score",
            ("organic_search_score", "search_score", "organic_score"),
        )
        _copy_first_present(
            normalized,
            "conversion_score",
            ("business_value_score", "conversion_potential_score", "commercial_score"),
        )
        _copy_first_present(
            normalized,
            "cta_angle",
            ("cta", "call_to_action", "conversion_angle"),
        )

        if "reasoning" not in normalized:
            _copy_first_present(
                normalized,
                "reasoning",
                ("rationale", "explanation", "summary", "why"),
            )

        if "total_score" not in normalized:
            score_values = [
                _coerce_score(normalized[field])
                for field in (
                    "trend_score",
                    "orbichat_relevance_score",
                    "seo_score",
                    "conversion_score",
                )
                if field in normalized
            ]
            if score_values:
                normalized["total_score"] = round(sum(score_values) / len(score_values))

        if "recommended" not in normalized and "total_score" in normalized:
            normalized["recommended"] = _coerce_score(normalized["total_score"]) >= 70

        if "search_intent" in normalized:
            normalized["search_intent"] = _normalize_search_intent(normalized["search_intent"])

        return normalized


class DailyTrendScanResult(APIModel):
    run_id: UUID
    candidate_count: int
    deduped_candidate_count: int
    topic_count: int
    provider_warnings: list[str]
    skipped_providers: list[str]


def _copy_first_present(target: dict[str, Any], canonical_key: str, alias_keys: tuple[str, ...]) -> None:
    if canonical_key in target and target[canonical_key] not in (None, ""):
        return

    for alias_key in alias_keys:
        value = target.get(alias_key)
        if value not in (None, ""):
            target[canonical_key] = value
            return


def _coerce_score(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return max(0, min(100, round(value)))
    if isinstance(value, str):
        stripped = value.strip().rstrip("%")
        try:
            return max(0, min(100, round(float(stripped))))
        except ValueError:
            return 0
    return 0


def _normalize_search_intent(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower().replace("_", " ").replace("-", " ")
    if normalized in {"info", "educational", "learn", "awareness"}:
        return "informational"
    if normalized in {"transactional", "commercial investigation", "buyer", "purchase"}:
        return "commercial"
    if normalized in {"versus", "vs", "alternative", "alternatives"}:
        return "comparison"
    if normalized in {"how to", "guide"}:
        return "tutorial"
    if normalized in {"informational", "commercial", "navigational", "comparison", "tutorial"}:
        return normalized
    return value
