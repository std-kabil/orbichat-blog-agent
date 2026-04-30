from datetime import UTC, datetime
from uuid import uuid4

from schemas.common import DraftStatus, RunStatus, SearchProvider, TopicStatus
from schemas.cost import CostSummary, ModelUsageSummary
from schemas.draft import DraftRead
from schemas.topic import TopicRead
from schemas.trend import TopicScoreOutput


def test_domain_enums_serialize_as_strings() -> None:
    assert RunStatus.QUEUED.value == "queued"
    assert TopicStatus.APPROVED.value == "approved"
    assert DraftStatus.NEEDS_REVIEW.value == "needs_review"
    assert SearchProvider.BRAVE.value == "brave"


def test_topic_schema_serializes_status() -> None:
    now = datetime(2026, 4, 30, tzinfo=UTC)

    topic = TopicRead(
        id=uuid4(),
        run_id=None,
        title="Best AI model for students",
        target_keyword="best ai model for students",
        search_intent="informational",
        summary=None,
        trend_score=80,
        orbichat_relevance_score=90,
        seo_score=75,
        conversion_score=70,
        total_score=79,
        recommended=True,
        reasoning=None,
        cta_angle=None,
        status=TopicStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
    )

    assert topic.model_dump(mode="json")["status"] == "candidate"


def test_draft_schema_serializes_status() -> None:
    now = datetime(2026, 4, 30, tzinfo=UTC)

    draft = DraftRead(
        id=uuid4(),
        topic_id=uuid4(),
        title="Draft title",
        slug="draft-title",
        meta_title=None,
        meta_description=None,
        target_keyword=None,
        markdown_content="# Draft",
        outline_json={},
        seo_json={},
        status=DraftStatus.DRAFT,
        version=1,
        publish_score=None,
        publish_ready=False,
        payload_post_id=None,
        created_at=now,
        updated_at=now,
    )

    assert draft.model_dump(mode="json")["status"] == "draft"


def test_cost_summary_schema_serializes_usage() -> None:
    summary = CostSummary(
        run_id=None,
        total_estimated_cost_usd="0.010000",
        total_input_tokens=10,
        total_output_tokens=20,
        llm_call_count=1,
        search_call_count=0,
        model_usage=[
            ModelUsageSummary(
                provider="openrouter",
                model="openai/gpt-5.4-mini",
                call_count=1,
                input_tokens=10,
                output_tokens=20,
                estimated_cost_usd="0.010000",
            )
        ],
    )

    assert summary.model_usage[0].provider == "openrouter"


def test_topic_score_output_accepts_provider_aliases() -> None:
    score = TopicScoreOutput.model_validate(
        {
            "topic_title": "Gemini vs Grok for research workflows",
            "primary_keyword": "Gemini vs Grok",
            "intent": "vs",
            "trendiness_score": "74",
            "orbichat_fit_score": 88,
            "organic_search_score": 71,
            "business_value_score": 62,
            "rationale": "Useful comparison topic for AI chat users.",
            "conversion_angle": "Compare models side by side with saved chats and seamless switching.",
        }
    )

    assert score.title == "Gemini vs Grok for research workflows"
    assert score.target_keyword == "Gemini vs Grok"
    assert score.search_intent == "comparison"
    assert score.trend_score == 74
    assert score.orbichat_relevance_score == 88
    assert score.seo_score == 71
    assert score.conversion_score == 62
    assert score.total_score == 74
    assert score.recommended is True
    assert score.cta_angle.startswith("Compare models")
