from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from agents.orchestrator import run_weekly_blog_generation
from agents.publish_checks import run_deterministic_publish_checks
from agents.source_research import build_source_queries, research_sources_for_topic
from agents.weekly_topic_selection import select_topic_for_weekly_draft
from app.config import Settings
from app.models import Topic
from jobs.weekly_blog_generation import weekly_blog_generation
from repositories.drafts import create_generated_draft
from repositories.fact_checks import create_fact_checks_from_verifications
from schemas.common import SearchProvider
from schemas.search import NormalizedSearchResult, SearchProviderWarning, SearchRouterResult
from schemas.workflow import (
    BlogDraftOutput,
    ClaimExtractionOutput,
    ClaimVerificationOutput,
    OutlineOutput,
    PublishJudgmentOutput,
    SEOAnglesOutput,
    SocialPostsOutput,
)


class FakeSearchRouter:
    def __init__(self, result: SearchRouterResult) -> None:
        self.result = result
        self.queries: list[str] = []

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
        self.queries.append(query)
        return self.result


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeScalarResult:
    def all(self) -> list[str]:
        return []


class FakePersistSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.added_many: list[object] = []
        self.commits = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    def add_all(self, items: list[object]) -> None:
        self.added_many.extend(items)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, item: object) -> None:
        return None

    def scalars(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult()


def _topic(**overrides: object) -> SimpleNamespace:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    values = {
        "id": uuid4(),
        "title": "Best AI chat apps for students",
        "target_keyword": "best AI chat apps",
        "search_intent": "commercial",
        "summary": None,
        "reasoning": "Strong fit.",
        "cta_angle": "Compare models in OrbiChat.",
        "total_score": 90,
        "created_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _source(**overrides: object) -> SimpleNamespace:
    values = {
        "id": uuid4(),
        "url": "https://example.com/source",
        "title": "Useful source",
        "publisher": None,
        "published_at": None,
        "snippet": "Source excerpt",
        "source_type": "tavily",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _seo() -> SEOAnglesOutput:
    return SEOAnglesOutput(
        primary_angle="Compare AI chat apps for student workflows.",
        alternative_angles=["Budget-friendly AI study workflows"],
        target_audience="Students",
        search_intent="commercial",
        primary_keyword="best AI chat apps",
        secondary_keywords=["AI chat for students"],
        recommended_title="Best AI Chat Apps for Students",
        meta_description="Compare AI chat apps for student research and writing.",
        cta_strategy="Mention OrbiChat once as a comparison workspace.",
    )


def _outline() -> OutlineOutput:
    return OutlineOutput(
        title="Best AI Chat Apps for Students",
        slug="best-ai-chat-apps-for-students",
        meta_title="Best AI Chat Apps for Students",
        meta_description="Compare AI chat apps for student research and writing.",
        sections=[{"heading": "What matters", "goal": "Set criteria", "key_points": ["Accuracy"]}],
        faq=[],
        internal_links=["/"],
        cta_placements=["conclusion"],
    )


def _draft(word_count: int = 920) -> BlogDraftOutput:
    body = " ".join(["useful"] * word_count)
    return BlogDraftOutput(
        title="Best AI Chat Apps for Students",
        slug="best-ai-chat-apps-for-students",
        meta_title="Best AI Chat Apps for Students",
        meta_description="Compare AI chat apps for student research and writing.",
        markdown_content=f"# Best AI Chat Apps for Students\n\n{body}",
        notes="Ready for review.",
    )


def _verification(**overrides: object) -> ClaimVerificationOutput:
    values: dict[str, object] = {
        "claim": "Students use AI chat apps for research.",
        "verdict": "supported",
        "severity": "low",
        "source_urls": ["https://example.com/source"],
        "explanation": "Supported by source.",
        "recommended_action": "cite",
    }
    values.update(overrides)
    return ClaimVerificationOutput.model_validate(values)


def test_weekly_llm_output_schemas_validate_expected_json() -> None:
    assert _seo().primary_keyword == "best AI chat apps"
    assert _outline().slug == "best-ai-chat-apps-for-students"
    assert _draft().markdown_content.startswith("# Best")
    assert ClaimExtractionOutput.model_validate(
        {
            "claims": [
                {
                    "claim": "OrbiChat supports multiple models.",
                    "claim_type": "product_feature",
                    "risk_level": "medium",
                    "needs_verification": True,
                }
            ]
        }
    ).claims[0].claim_type == "product_feature"
    assert _verification().verdict == "supported"
    assert PublishJudgmentOutput(
        publish_ready=True,
        score=91,
        risk_level="low",
        required_fixes=[],
        reasoning="Passes review.",
    ).score == 91
    assert SocialPostsOutput(
        posts=[{"platform": "linkedin", "content": "Draft post", "metadata": {}}]
    ).posts[0].platform == "linkedin"


def test_topic_selection_fails_clearly_when_no_topic(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("agents.weekly_topic_selection.select_next_weekly_topic", lambda db: None)

    with pytest.raises(RuntimeError, match="No approved or recommended topic"):
        select_topic_for_weekly_draft(cast(Session, SimpleNamespace()))


def test_source_queries_use_topic_keyword_and_intent() -> None:
    queries = build_source_queries(cast(Topic, _topic()))

    assert queries[0] == "Best AI chat apps for students best AI chat apps commercial"
    assert any("sources data examples" in query for query in queries)


@pytest.mark.anyio
async def test_source_research_saves_sources_and_preserves_warnings(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    created_results: list[NormalizedSearchResult] = []
    result = SearchRouterResult(
        results=[
            NormalizedSearchResult(
                title="Source",
                url="https://example.com/source",
                snippet="Snippet",
                published_at=None,
                source_provider=SearchProvider.TAVILY,
                raw={"id": "1"},
            )
        ],
        warnings=[SearchProviderWarning(provider=SearchProvider.EXA, message="timeout")],
    )

    def fake_create(db: object, *, topic_id: UUID, results: list[NormalizedSearchResult]) -> list[object]:
        created_results.extend(results)
        return [_source()]

    monkeypatch.setattr("agents.source_research.create_sources_from_search_results", fake_create)

    sources, warnings = await research_sources_for_topic(
        settings=Settings(app_env="test", tavily_api_key="tavily", sentry_dsn=None),
        db=cast(Session, SimpleNamespace()),
        run_id=uuid4(),
        topic=cast(Topic, _topic()),
        search_router=FakeSearchRouter(result),
    )

    assert len(sources) == 1
    assert created_results[0].url == "https://example.com/source"
    assert [f"{warning.provider.value}: {warning.message}" for warning in warnings] == ["exa: timeout"]


def test_deterministic_publish_checks_block_unsafe_and_auto_publish_false() -> None:
    checks = run_deterministic_publish_checks(
        settings=Settings(app_env="test", auto_publish=False, sentry_dsn=None),
        title="Best AI Chat Apps",
        slug="best-ai-chat-apps",
        meta_description="A practical comparison.",
        markdown_content="# Title\n\n" + " ".join(["useful"] * 920),
        verifications=[_verification()],
    )

    assert checks.publish_ready is False
    assert "AUTO_PUBLISH is false" in checks.blockers


def test_deterministic_publish_checks_block_high_unsupported_claim() -> None:
    checks = run_deterministic_publish_checks(
        settings=Settings(app_env="test", auto_publish=True, sentry_dsn=None),
        title="Best AI Chat Apps",
        slug="best-ai-chat-apps",
        meta_description="A practical comparison.",
        markdown_content="# Title\n\n" + " ".join(["useful"] * 920),
        verifications=[_verification(verdict="unsupported", severity="high", source_urls=[])],
    )

    assert checks.publish_ready is False
    assert "Article has a high-severity unsupported claim" in checks.blockers


def test_draft_creation_stores_generated_metadata() -> None:
    fake_db = FakePersistSession()
    topic_id = uuid4()

    draft = create_generated_draft(
        cast(Session, fake_db),
        topic_id=topic_id,
        draft_output=_draft(),
        outline=_outline(),
        seo_angles=_seo(),
        target_keyword="best AI chat apps",
    )

    assert draft in fake_db.added
    assert draft.topic_id == topic_id
    assert draft.slug == "best-ai-chat-apps-for-students"
    assert draft.outline_json["title"] == "Best AI Chat Apps for Students"
    assert draft.seo_json["primary_keyword"] == "best AI chat apps"
    assert draft.meta_title == "Best AI Chat Apps for Students"
    assert draft.meta_description == "Compare AI chat apps for student research and writing."
    assert draft.markdown_content.startswith("# Best")


def test_fact_check_creation_stores_verification_records() -> None:
    fake_db = FakePersistSession()
    draft_id = uuid4()

    fact_checks = create_fact_checks_from_verifications(
        cast(Session, fake_db),
        draft_id=draft_id,
        verifications=[_verification()],
    )

    assert fact_checks == fake_db.added_many
    assert fact_checks[0].draft_id == draft_id
    assert fact_checks[0].claim == "Students use AI chat apps for research."
    assert fact_checks[0].source_urls_json == ["https://example.com/source"]


@pytest.mark.anyio
async def test_weekly_orchestrator_completed_with_warning_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = uuid4()
    topic = _topic()
    draft_id = uuid4()
    calls: list[str] = []

    monkeypatch.setattr("agents.orchestrator.mark_run_running", lambda db, run_id: calls.append("running"))
    monkeypatch.setattr("agents.orchestrator.get_topic", lambda db, topic_id: topic)
    monkeypatch.setattr(
        "agents.orchestrator.research_sources_for_topic",
        lambda **kwargs: _async_return(([_source()], [])),
    )
    monkeypatch.setattr("agents.orchestrator.generate_seo_angles", lambda **kwargs: _async_return(_seo()))
    monkeypatch.setattr("agents.orchestrator.generate_outline", lambda **kwargs: _async_return(_outline()))
    monkeypatch.setattr(
        "agents.orchestrator.write_article_draft",
        lambda **kwargs: _async_return(_draft()),
    )
    monkeypatch.setattr(
        "agents.orchestrator.extract_claims",
        lambda **kwargs: _async_return(ClaimExtractionOutput(claims=[])),
    )
    monkeypatch.setattr(
        "agents.orchestrator.verify_claims",
        lambda **kwargs: _async_return([_verification()]),
    )
    monkeypatch.setattr("agents.orchestrator.polish_brand_draft", lambda **kwargs: _async_return(_draft()))
    monkeypatch.setattr(
        "agents.orchestrator.create_generated_draft",
        lambda *args, **kwargs: SimpleNamespace(id=draft_id, slug="best-ai-chat-apps-for-students"),
    )
    monkeypatch.setattr("agents.orchestrator.attach_sources_to_draft", lambda *args, **kwargs: 1)
    monkeypatch.setattr(
        "agents.orchestrator.create_fact_checks_from_verifications",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("agents.orchestrator.mark_topic_drafted", lambda db, topic_id: None)

    async def fake_social_posts(**kwargs: object) -> SocialPostsOutput:
        raise RuntimeError("social failed")

    monkeypatch.setattr("agents.orchestrator.generate_social_posts", fake_social_posts)
    monkeypatch.setattr(
        "agents.orchestrator.judge_publish_readiness",
        lambda **kwargs: _async_return(
            PublishJudgmentOutput(
                publish_ready=True,
                score=90,
                risk_level="low",
                required_fixes=[],
                reasoning="Good.",
            )
        ),
    )
    monkeypatch.setattr("agents.orchestrator.update_publish_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr("agents.orchestrator.update_run_totals", lambda db, run_id, costs: None)
    monkeypatch.setattr(
        "agents.orchestrator.summarize_costs",
        lambda db, run_id: SimpleNamespace(
            total_estimated_cost_usd=0,
            total_input_tokens=0,
            total_output_tokens=0,
        ),
    )
    monkeypatch.setattr(
        "agents.orchestrator.mark_run_completed",
        lambda db, run_id, metadata_json: calls.append(f"completed:{len(metadata_json['warnings'])}"),
    )

    result = await run_weekly_blog_generation(
        settings=Settings(app_env="test", auto_publish=False, sentry_dsn=None),
        db=cast(Session, SimpleNamespace()),
        run_id=run_id,
        topic_id=cast(UUID, topic.id),
    )

    assert result.status == "completed"
    assert result.draft_id == draft_id
    assert any("social_posts_failed" in warning for warning in result.warnings)
    assert calls == ["running", "completed:2"]


@pytest.mark.anyio
async def test_weekly_orchestrator_marks_failed_before_draft(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = uuid4()
    calls: list[str] = []

    monkeypatch.setattr("agents.orchestrator.mark_run_running", lambda db, run_id: calls.append("running"))
    monkeypatch.setattr("agents.orchestrator.get_topic", lambda db, topic_id: _topic(id=topic_id))

    async def fail_research(**kwargs: object) -> tuple[list[object], list[object]]:
        raise RuntimeError("no sources")

    monkeypatch.setattr("agents.orchestrator.research_sources_for_topic", fail_research)
    monkeypatch.setattr(
        "agents.orchestrator.mark_run_failed_with_metadata",
        lambda db, run_id, error_message, metadata_json: calls.append(
            f"failed:{error_message}:{metadata_json['draft_id']}"
        ),
    )

    with pytest.raises(RuntimeError, match="no sources"):
        await run_weekly_blog_generation(
            settings=Settings(app_env="test", sentry_dsn=None),
            db=cast(Session, SimpleNamespace()),
            run_id=run_id,
            topic_id=uuid4(),
        )

    assert calls == ["running", "failed:no sources:None"]


def test_weekly_job_closes_session_and_returns_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_session = FakeSession()
    run_id = uuid4()

    monkeypatch.setattr("jobs.weekly_blog_generation.SessionLocal", lambda: fake_session)
    monkeypatch.setattr("jobs.weekly_blog_generation.get_settings", lambda: Settings(app_env="test"))
    monkeypatch.setattr(
        "jobs.weekly_blog_generation.run_weekly_blog_generation",
        lambda **kwargs: _async_return(
            SimpleNamespace(
                model_dump=lambda mode: {
                    "run_id": str(run_id),
                    "status": "completed",
                    "draft_id": str(uuid4()),
                }
            )
        ),
    )

    result = weekly_blog_generation(str(run_id))

    assert result["status"] == "completed"
    assert fake_session.closed is True


async def _async_return(value: object) -> object:
    return value
