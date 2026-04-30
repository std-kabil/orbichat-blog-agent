"""create initial agent schema

Revision ID: 20260430_0001
Revises:
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260430_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), server_default="0", nullable=False),
        sa.Column("total_input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_run_type"), "agent_runs", ["run_type"], unique=False)
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("target_keyword", sa.Text(), nullable=True),
        sa.Column("search_intent", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("trend_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("orbichat_relevance_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("seo_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conversion_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recommended", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("cta_angle", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="candidate", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_run_id"), "topics", ["run_id"], unique=False)
    op.create_index(op.f("ix_topics_status"), "topics", ["status"], unique=False)

    op.create_table(
        "trend_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_score", sa.Numeric(12, 6), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trend_candidates_run_id"), "trend_candidates", ["run_id"], unique=False)
    op.create_index(op.f("ix_trend_candidates_source"), "trend_candidates", ["source"], unique=False)

    op.create_table(
        "blog_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("meta_title", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("target_keyword", sa.Text(), nullable=True),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column(
            "outline_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "seo_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("publish_score", sa.Integer(), nullable=True),
        sa.Column("publish_ready", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("payload_post_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blog_drafts_slug"), "blog_drafts", ["slug"], unique=True)
    op.create_index(op.f("ix_blog_drafts_status"), "blog_drafts", ["status"], unique=False)
    op.create_index(op.f("ix_blog_drafts_topic_id"), "blog_drafts", ["topic_id"], unique=False)

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload_post_id", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("page_views", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unique_visitors", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cta_clicks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("signups", sa.Integer(), server_default="0", nullable=False),
        sa.Column("search_impressions", sa.Integer(), nullable=True),
        sa.Column("search_clicks", sa.Integer(), nullable=True),
        sa.Column("avg_position", sa.Numeric(8, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analytics_snapshots_date"), "analytics_snapshots", ["date"], unique=False)
    op.create_index(op.f("ix_analytics_snapshots_draft_id"), "analytics_snapshots", ["draft_id"], unique=False)

    op.create_table(
        "fact_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=80), nullable=True),
        sa.Column("verdict", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "source_urls_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("recommended_action", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fact_checks_draft_id"), "fact_checks", ["draft_id"], unique=False)
    op.create_index(op.f("ix_fact_checks_severity"), "fact_checks", ["severity"], unique=False)
    op.create_index(op.f("ix_fact_checks_verdict"), "fact_checks", ["verdict"], unique=False)

    op.create_table(
        "llm_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_calls_draft_id"), "llm_calls", ["draft_id"], unique=False)
    op.create_index(op.f("ix_llm_calls_provider"), "llm_calls", ["provider"], unique=False)
    op.create_index(op.f("ix_llm_calls_run_id"), "llm_calls", ["run_id"], unique=False)
    op.create_index(op.f("ix_llm_calls_task_name"), "llm_calls", ["task_name"], unique=False)
    op.create_index(op.f("ix_llm_calls_topic_id"), "llm_calls", ["topic_id"], unique=False)

    op.create_table(
        "search_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("result_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_calls_draft_id"), "search_calls", ["draft_id"], unique=False)
    op.create_index(op.f("ix_search_calls_provider"), "search_calls", ["provider"], unique=False)
    op.create_index(op.f("ix_search_calls_run_id"), "search_calls", ["run_id"], unique=False)
    op.create_index(op.f("ix_search_calls_topic_id"), "search_calls", ["topic_id"], unique=False)

    op.create_table(
        "social_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="draft", nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_social_posts_draft_id"), "social_posts", ["draft_id"], unique=False)
    op.create_index(op.f("ix_social_posts_platform"), "social_posts", ["platform"], unique=False)
    op.create_index(op.f("ix_social_posts_status"), "social_posts", ["status"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("credibility_score", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("used_in_article", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["blog_drafts.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sources_draft_id"), "sources", ["draft_id"], unique=False)
    op.create_index(op.f("ix_sources_topic_id"), "sources", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sources_topic_id"), table_name="sources")
    op.drop_index(op.f("ix_sources_draft_id"), table_name="sources")
    op.drop_table("sources")
    op.drop_index(op.f("ix_social_posts_status"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_platform"), table_name="social_posts")
    op.drop_index(op.f("ix_social_posts_draft_id"), table_name="social_posts")
    op.drop_table("social_posts")
    op.drop_index(op.f("ix_search_calls_topic_id"), table_name="search_calls")
    op.drop_index(op.f("ix_search_calls_run_id"), table_name="search_calls")
    op.drop_index(op.f("ix_search_calls_provider"), table_name="search_calls")
    op.drop_index(op.f("ix_search_calls_draft_id"), table_name="search_calls")
    op.drop_table("search_calls")
    op.drop_index(op.f("ix_llm_calls_topic_id"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_task_name"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_run_id"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_provider"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_draft_id"), table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_index(op.f("ix_fact_checks_verdict"), table_name="fact_checks")
    op.drop_index(op.f("ix_fact_checks_severity"), table_name="fact_checks")
    op.drop_index(op.f("ix_fact_checks_draft_id"), table_name="fact_checks")
    op.drop_table("fact_checks")
    op.drop_index(op.f("ix_analytics_snapshots_draft_id"), table_name="analytics_snapshots")
    op.drop_index(op.f("ix_analytics_snapshots_date"), table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
    op.drop_index(op.f("ix_blog_drafts_topic_id"), table_name="blog_drafts")
    op.drop_index(op.f("ix_blog_drafts_status"), table_name="blog_drafts")
    op.drop_index(op.f("ix_blog_drafts_slug"), table_name="blog_drafts")
    op.drop_table("blog_drafts")
    op.drop_index(op.f("ix_trend_candidates_source"), table_name="trend_candidates")
    op.drop_index(op.f("ix_trend_candidates_run_id"), table_name="trend_candidates")
    op.drop_table("trend_candidates")
    op.drop_index(op.f("ix_topics_status"), table_name="topics")
    op.drop_index(op.f("ix_topics_run_id"), table_name="topics")
    op.drop_table("topics")
    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_run_type"), table_name="agent_runs")
    op.drop_table("agent_runs")
