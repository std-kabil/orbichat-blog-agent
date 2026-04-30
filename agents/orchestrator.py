from uuid import UUID

from sqlalchemy.orm import Session

from agents.topic_scorer import score_and_store_topics
from agents.trend_discovery import (
    TrendSearchRouter,
    dedupe_trend_candidates,
    discover_trend_candidates,
    group_topic_candidates,
)
from agents.blog_generation import (
    extract_claims,
    generate_outline,
    generate_seo_angles,
    generate_social_posts,
    judge_publish_readiness,
    polish_brand_draft,
    verify_claims,
    write_article_draft,
)
from agents.publish_checks import run_deterministic_publish_checks
from agents.source_research import SourceSearchRouter, research_sources_for_topic
from agents.weekly_topic_selection import select_topic_for_weekly_draft
from app.config import Settings
from repositories.drafts import create_generated_draft, update_publish_metadata
from repositories.fact_checks import create_fact_checks_from_verifications
from repositories.social_posts import create_draft_social_posts
from repositories.sources import attach_sources_to_draft
from repositories.costs import summarize_costs
from repositories.runs import (
    mark_run_completed,
    mark_run_failed,
    mark_run_failed_with_metadata,
    mark_run_running,
    update_run_totals,
)
from repositories.topics import get_topic, mark_topic_drafted
from schemas.common import DraftStatus
from schemas.trend import DailyTrendScanResult
from schemas.workflow import WeeklyBlogGenerationResult
from services.monitoring import capture_run_exception, log_run_event


async def run_daily_trend_scan(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    search_router: TrendSearchRouter | None = None,
) -> DailyTrendScanResult:
    mark_run_running(db, run_id)
    log_run_event(event="daily_trend_scan_start", run_id=run_id, status="running")

    try:
        candidates, provider_warnings, skipped_providers = await discover_trend_candidates(
            settings=settings,
            db=db,
            run_id=run_id,
            search_router=search_router,
        )
        deduped_candidates = dedupe_trend_candidates(candidates)
        if not deduped_candidates:
            raise RuntimeError("Daily trend scan found no trend candidates")

        topic_inputs = group_topic_candidates(deduped_candidates)
        scored_topics = await score_and_store_topics(
            settings=settings,
            db=db,
            run_id=run_id,
            topic_inputs=topic_inputs,
        )

        costs = summarize_costs(db, run_id=run_id)
        update_run_totals(db, run_id, costs)

        result = DailyTrendScanResult(
            run_id=run_id,
            candidate_count=len(candidates),
            deduped_candidate_count=len(deduped_candidates),
            topic_count=len(scored_topics),
            provider_warnings=[
                f"{warning.provider.value}: {warning.message}" for warning in provider_warnings
            ],
            skipped_providers=[provider.value for provider in skipped_providers],
        )
        mark_run_completed(db, run_id, metadata_json=result.model_dump(mode="json"))
        log_run_event(event="daily_trend_scan_complete", run_id=run_id, status="completed")
        return result
    except Exception as exc:
        mark_run_failed(db, run_id, str(exc))
        log_run_event(
            event="daily_trend_scan_failed",
            run_id=run_id,
            status="failed",
            message=str(exc),
        )
        capture_run_exception(settings=settings, exc=exc, run_id=run_id, task_name="daily_trend_scan")
        raise


async def run_weekly_blog_generation(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID | None = None,
    search_router: SourceSearchRouter | None = None,
) -> WeeklyBlogGenerationResult:
    mark_run_running(db, run_id)
    log_run_event(event="weekly_blog_generation_start", run_id=run_id, status="running")
    selected_topic_id: UUID | None = topic_id
    draft_id: UUID | None = None
    warnings: list[str] = []
    provider_warning_messages: list[str] = []

    try:
        topic = get_topic(db, topic_id) if topic_id is not None else select_topic_for_weekly_draft(db)
        if topic is None:
            raise RuntimeError(f"Topic {topic_id} was not found")
        selected_topic_id = topic.id

        sources, provider_warnings = await research_sources_for_topic(
            settings=settings,
            db=db,
            run_id=run_id,
            topic=topic,
            search_router=search_router,
        )
        provider_warning_messages = [
            f"{warning.provider.value}: {warning.message}" for warning in provider_warnings
        ]
        for warning in provider_warning_messages:
            log_run_event(
                event="source_provider_warning",
                run_id=run_id,
                topic_id=topic.id,
                status="warning",
                message=warning,
            )

        seo_angles = await generate_seo_angles(
            settings=settings,
            db=db,
            run_id=run_id,
            topic=topic,
            sources=sources,
        )
        outline = await generate_outline(
            settings=settings,
            db=db,
            run_id=run_id,
            topic=topic,
            sources=sources,
            seo_angles=seo_angles,
        )
        draft_output = await write_article_draft(
            settings=settings,
            db=db,
            run_id=run_id,
            topic=topic,
            sources=sources,
            seo_angles=seo_angles,
            outline=outline,
        )
        extracted_claims = await extract_claims(
            settings=settings,
            db=db,
            run_id=run_id,
            topic_id=topic.id,
            draft=draft_output,
        )
        verifications = await verify_claims(
            settings=settings,
            db=db,
            run_id=run_id,
            topic_id=topic.id,
            draft_id=None,
            sources=sources,
            claims=extracted_claims,
        )
        polished_draft = await polish_brand_draft(
            settings=settings,
            db=db,
            run_id=run_id,
            topic_id=topic.id,
            draft_id=None,
            draft=draft_output,
            verifications=verifications,
        )

        draft = create_generated_draft(
            db,
            topic_id=topic.id,
            draft_output=polished_draft,
            outline=outline,
            seo_angles=seo_angles,
            target_keyword=topic.target_keyword,
        )
        draft_id = draft.id
        attach_sources_to_draft(db, source_ids=[source.id for source in sources], draft_id=draft.id)
        create_fact_checks_from_verifications(db, draft_id=draft.id, verifications=verifications)
        mark_topic_drafted(db, topic.id)

        try:
            social_posts = await generate_social_posts(
                settings=settings,
                db=db,
                run_id=run_id,
                topic_id=topic.id,
                draft_id=draft.id,
                draft=polished_draft,
            )
            create_draft_social_posts(db, draft_id=draft.id, posts=social_posts.posts)
        except Exception as exc:
            warnings.append(f"social_posts_failed: {exc}")

        deterministic_checks = run_deterministic_publish_checks(
            settings=settings,
            title=polished_draft.title,
            slug=draft.slug,
            meta_description=polished_draft.meta_description,
            markdown_content=polished_draft.markdown_content,
            verifications=verifications,
        )
        publish_score: int | None = None
        publish_ready = False

        try:
            judgment = await judge_publish_readiness(
                settings=settings,
                db=db,
                run_id=run_id,
                topic_id=topic.id,
                draft_id=draft.id,
                draft=polished_draft,
                deterministic_blockers=deterministic_checks.blockers,
                verifications=verifications,
            )
            publish_score = judgment.score
            publish_ready = (
                deterministic_checks.publish_ready
                and judgment.publish_ready
                and settings.auto_publish
                and judgment.score >= settings.min_publish_score
            )
            if deterministic_checks.blockers:
                warnings.extend(f"publish_blocked: {blocker}" for blocker in deterministic_checks.blockers)
            if judgment.required_fixes:
                warnings.extend(f"publish_fix_required: {fix}" for fix in judgment.required_fixes)
        except Exception as exc:
            warnings.append(f"publish_judgment_failed: {exc}")
            if deterministic_checks.blockers:
                warnings.extend(f"publish_blocked: {blocker}" for blocker in deterministic_checks.blockers)

        update_publish_metadata(
            db,
            draft_id=draft.id,
            publish_score=publish_score,
            publish_ready=publish_ready,
            status=DraftStatus.DRAFT,
        )

        costs = summarize_costs(db, run_id=run_id)
        update_run_totals(db, run_id, costs)

        result = WeeklyBlogGenerationResult(
            run_id=run_id,
            topic_id=topic.id,
            draft_id=draft.id,
            status="completed",
            warnings=warnings,
            provider_warnings=provider_warning_messages,
            publish_ready=publish_ready,
            publish_score=publish_score,
        )
        mark_run_completed(db, run_id, metadata_json=result.model_dump(mode="json"))
        log_run_event(
            event="weekly_blog_generation_complete",
            run_id=run_id,
            topic_id=topic.id,
            draft_id=draft.id,
            status="completed",
        )
        return result
    except Exception as exc:
        result = WeeklyBlogGenerationResult(
            run_id=run_id,
            topic_id=selected_topic_id,
            draft_id=draft_id,
            status="failed",
            warnings=warnings,
            provider_warnings=provider_warning_messages,
            publish_ready=False,
            publish_score=None,
        )
        mark_run_failed_with_metadata(
            db,
            run_id,
            error_message=str(exc),
            metadata_json=result.model_dump(mode="json"),
        )
        log_run_event(
            event="weekly_blog_generation_failed",
            run_id=run_id,
            topic_id=selected_topic_id,
            draft_id=draft_id,
            status="failed",
            message=str(exc),
        )
        capture_run_exception(
            settings=settings,
            exc=exc,
            run_id=run_id,
            topic_id=selected_topic_id,
            draft_id=draft_id,
            task_name="weekly_blog_generation",
        )
        raise
