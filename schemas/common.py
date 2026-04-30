from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(APIModel):
    status: str
    service: str


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunType(StrEnum):
    DAILY_SCAN = "daily_scan"
    WEEKLY_BLOG_GENERATION = "weekly_blog_generation"
    MANUAL_DRAFT = "manual_draft"
    VERIFY_DRAFT = "verify_draft"
    ANALYTICS_SYNC = "analytics_sync"


class TopicStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    DRAFTED = "drafted"
    PUBLISHED = "published"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class SearchProvider(StrEnum):
    TAVILY = "tavily"
    EXA = "exa"
    BRAVE = "brave"


class MetadataMixin(APIModel):
    metadata_json: dict[str, Any]
