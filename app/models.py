from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid_primary_key() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def timestamp_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_timestamp_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def json_object_column() -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


def json_array_column() -> Mapped[list[str]]:
    return mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    run_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default="0")
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = json_object_column()
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = updated_timestamp_column()

    trend_candidates: Mapped[list["TrendCandidate"]] = relationship(back_populates="run")
    topics: Mapped[list["Topic"]] = relationship(back_populates="run")
    llm_calls: Mapped[list["LLMCall"]] = relationship(back_populates="run")
    search_calls: Mapped[list["SearchCall"]] = relationship(back_populates="run")


class TrendCandidate(Base):
    __tablename__ = "trend_candidates"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    metadata_json: Mapped[dict[str, Any]] = json_object_column()
    created_at: Mapped[datetime] = timestamp_column()

    run: Mapped[AgentRun] = relationship(back_populates="trend_candidates")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    target_keyword: Mapped[str | None] = mapped_column(Text)
    search_intent: Mapped[str | None] = mapped_column(String(80))
    summary: Mapped[str | None] = mapped_column(Text)
    trend_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    orbichat_relevance_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    seo_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    conversion_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reasoning: Mapped[str | None] = mapped_column(Text)
    cta_angle: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="candidate", index=True)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = updated_timestamp_column()

    run: Mapped[AgentRun | None] = relationship(back_populates="topics")
    sources: Mapped[list["Source"]] = relationship(back_populates="topic")
    drafts: Mapped[list["BlogDraft"]] = relationship(back_populates="topic")
    llm_calls: Mapped[list["LLMCall"]] = relationship(back_populates="topic")
    search_calls: Mapped[list["SearchCall"]] = relationship(back_populates="topic")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("blog_drafts.id"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    credibility_score: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str | None] = mapped_column(String(80))
    used_in_article: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    metadata_json: Mapped[dict[str, Any]] = json_object_column()
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = updated_timestamp_column()

    topic: Mapped[Topic | None] = relationship(back_populates="sources")
    draft: Mapped["BlogDraft | None"] = relationship(back_populates="sources")


class BlogDraft(Base):
    __tablename__ = "blog_drafts"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    meta_title: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str | None] = mapped_column(Text)
    target_keyword: Mapped[str | None] = mapped_column(Text)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    outline_json: Mapped[dict[str, Any]] = json_object_column()
    seo_json: Mapped[dict[str, Any]] = json_object_column()
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    publish_score: Mapped[int | None] = mapped_column(Integer)
    publish_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    payload_post_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = updated_timestamp_column()

    topic: Mapped[Topic] = relationship(back_populates="drafts")
    sources: Mapped[list[Source]] = relationship(back_populates="draft")
    fact_checks: Mapped[list["FactCheck"]] = relationship(back_populates="draft")
    social_posts: Mapped[list["SocialPost"]] = relationship(back_populates="draft")
    llm_calls: Mapped[list["LLMCall"]] = relationship(back_populates="draft")
    search_calls: Mapped[list["SearchCall"]] = relationship(back_populates="draft")
    analytics_snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(back_populates="draft")


class FactCheck(Base):
    __tablename__ = "fact_checks"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("blog_drafts.id"), nullable=False, index=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str | None] = mapped_column(String(80))
    verdict: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    explanation: Mapped[str | None] = mapped_column(Text)
    source_urls_json: Mapped[list[str]] = json_array_column()
    recommended_action: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = timestamp_column()

    draft: Mapped[BlogDraft] = relationship(back_populates="fact_checks")


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("blog_drafts.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="draft", index=True)
    metadata_json: Mapped[dict[str, Any]] = json_object_column()
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = updated_timestamp_column()

    draft: Mapped[BlogDraft] = relationship(back_populates="social_posts")


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("blog_drafts.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    task_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp_column()

    run: Mapped[AgentRun | None] = relationship(back_populates="llm_calls")
    draft: Mapped[BlogDraft | None] = relationship(back_populates="llm_calls")
    topic: Mapped[Topic | None] = relationship(back_populates="llm_calls")


class SearchCall(Base):
    __tablename__ = "search_calls"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("blog_drafts.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp_column()

    run: Mapped[AgentRun | None] = relationship(back_populates="search_calls")
    topic: Mapped[Topic | None] = relationship(back_populates="search_calls")
    draft: Mapped[BlogDraft | None] = relationship(back_populates="search_calls")


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = uuid_primary_key()
    draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("blog_drafts.id"), index=True)
    payload_post_id: Mapped[str | None] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    page_views: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    unique_visitors: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cta_clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    signups: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    search_impressions: Mapped[int | None] = mapped_column(Integer)
    search_clicks: Mapped[int | None] = mapped_column(Integer)
    avg_position: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    created_at: Mapped[datetime] = timestamp_column()

    draft: Mapped[BlogDraft | None] = relationship(back_populates="analytics_snapshots")
