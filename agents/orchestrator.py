from typing import Any
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
from repositories.drafts import create_generated_draft, get_draft, update_publish_metadata
from repositories.fact_checks import create_fact_checks_from_verifications
from repositories.social_posts import create_draft_social_posts
from repositories.sources import attach_sources_to_draft, list_sources_by_ids
from repositories.costs import summarize_costs
from repositories.runs import (
    get_run,
    mark_run_completed,
    mark_run_failed,
    mark_run_failed_with_metadata,
    mark_run_running,
    update_run_metadata,
    update_run_totals,
)
from repositories.topics import get_topic, mark_topic_drafted
from schemas.common import DraftStatus
from schemas.trend import DailyTrendScanResult
from schemas.workflow import (
    BlogDraftOutput,
    ClaimExtractionOutput,
    ClaimVerificationOutput,
    OutlineOutput,
    PublishJudgmentOutput,
    SEOAnglesOutput,
    WeeklyBlogGenerationResult,
)
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


WEEKLY_CHECKPOINTS_KEY = "checkpoints"


async def run_weekly_blog_generation(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    topic_id: UUID | None = None,
    search_router: SourceSearchRouter | None = None,
    resume: bool = False,
) -> WeeklyBlogGenerationResult:
    run = get_run(db, run_id) if resume else None
    run_metadata = dict(run.metadata_json or {}) if run is not None else {}
    checkpoints = _weekly_checkpoints(run_metadata) if resume else {}
    if resume and topic_id is None:
        topic_id = _metadata_uuid(run_metadata, "topic_id")

    mark_run_running(db, run_id)
    log_run_event(
        event="weekly_blog_generation_resume_start" if resume else "weekly_blog_generation_start",
        run_id=run_id,
        status="running",
    )
    selected_topic_id: UUID | None = topic_id
    draft_id: UUID | None = _metadata_uuid(run_metadata, "draft_id") if resume else None
    warnings: list[str] = list(run_metadata.get("warnings", [])) if resume else []
    provider_warning_messages: list[str] = (
        list(run_metadata.get("provider_warnings", [])) if resume else []
    )
    if resume:
        warnings.append("resumed_from_failed_run")

    try:
        topic = get_topic(db, topic_id) if topic_id is not None else select_topic_for_weekly_draft(db)
        if topic is None:
            raise RuntimeError(f"Topic {topic_id} was not found")
        selected_topic_id = topic.id
        run_metadata = _checkpoint_weekly_value(
            db,
            run_id,
            run_metadata,
            "topic_selected",
            {"topic_id": str(topic.id)},
            topic_id=topic.id,
            draft_id=draft_id,
            warnings=warnings,
            provider_warnings=provider_warning_messages,
        )

        if resume and "sources" in checkpoints:
            source_ids = [
                UUID(source_id)
                for source_id in checkpoints["sources"].get("source_ids", [])
                if isinstance(source_id, str)
            ]
            sources = list_sources_by_ids(db, source_ids)
        else:
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
            run_metadata = _checkpoint_weekly_value(
                db,
                run_id,
                run_metadata,
                "sources",
                {"source_ids": [str(source.id) for source in sources]},
                topic_id=topic.id,
                draft_id=draft_id,
                warnings=warnings,
                provider_warnings=provider_warning_messages,
            )

        if resume and "seo_angles" in checkpoints:
            seo_angles = SEOAnglesOutput.model_validate(checkpoints["seo_angles"])
        else:
            seo_angles = await generate_seo_angles(
                settings=settings,
                db=db,
                run_id=run_id,
                topic=topic,
                sources=sources,
            )
            run_metadata = _checkpoint_weekly_model(
                db,
                run_id,
                run_metadata,
                "seo_angles",
                seo_angles,
                topic_id=topic.id,
                draft_id=draft_id,
                warnings=warnings,
                provider_warnings=provider_warning_messages,
            )

        if resume and "outline" in checkpoints:
            outline = OutlineOutput.model_validate(checkpoints["outline"])
        else:
            outline = await generate_outline(
                settings=settings,
                db=db,
                run_id=run_id,
                topic=topic,
                sources=sources,
                seo_angles=seo_angles,
            )
            run_metadata = _checkpoint_weekly_model(
                db,
                run_id,
                run_metadata,
                "outline",
                outline,
                topic_id=topic.id,
                draft_id=draft_id,
                warnings=warnings,
                provider_warnings=provider_warning_messages,
            )

        if resume and "article_draft" in checkpoints:
            draft_output = BlogDraftOutput.model_validate(checkpoints["article_draft"])
        else:
            draft_output = await write_article_draft(
                settings=settings,
                db=db,
                run_id=run_id,
                topic=topic,
                sources=sources,
                seo_angles=seo_angles,
                outline=outline,
            )
            run_metadata = _checkpoint_weekly_model(
                db,
                run_id,
                run_metadata,
                "article_draft",
                draft_output,
                topic_id=topic.id,
                draft_id=draft_id,
                warnings=warnings,
                provider_warnings=provider_warning_messages,
            )

        verifications = []
        verification_failed = False
        polished_draft = draft_output
        try:
            if resume and "claim_extraction" in checkpoints:
                extracted_claims = ClaimExtractionOutput.model_validate(
                    checkpoints["claim_extraction"]
                )
            else:
                extracted_claims = await extract_claims(
                    settings=settings,
                    db=db,
                    run_id=run_id,
                    topic_id=topic.id,
                    draft=draft_output,
                )
                run_metadata = _checkpoint_weekly_model(
                    db,
                    run_id,
                    run_metadata,
                    "claim_extraction",
                    extracted_claims,
                    topic_id=topic.id,
                    draft_id=draft_id,
                    warnings=warnings,
                    provider_warnings=provider_warning_messages,
                )

            if resume and "claim_verification" in checkpoints:
                verifications = [
                    ClaimVerificationOutput.model_validate(item)
                    for item in checkpoints["claim_verification"]
                ]
            else:
                verifications = await verify_claims(
                    settings=settings,
                    db=db,
                    run_id=run_id,
                    topic_id=topic.id,
                    draft_id=None,
                    sources=sources,
                    claims=extracted_claims,
                )
                run_metadata = _checkpoint_weekly_value(
                    db,
                    run_id,
                    run_metadata,
                    "claim_verification",
                    [item.model_dump(mode="json") for item in verifications],
                    topic_id=topic.id,
                    draft_id=draft_id,
                    warnings=warnings,
                    provider_warnings=provider_warning_messages,
                )
        except Exception as exc:
            verification_failed = True
            warnings.append(f"claim_verification_failed: {exc}")

        if resume and "brand_polish" in checkpoints:
            polished_draft = BlogDraftOutput.model_validate(checkpoints["brand_polish"])
        elif verifications:
            try:
                polished_draft = await polish_brand_draft(
                    settings=settings,
                    db=db,
                    run_id=run_id,
                    topic_id=topic.id,
                    draft_id=None,
                    draft=draft_output,
                    verifications=verifications,
                )
                run_metadata = _checkpoint_weekly_model(
                    db,
                    run_id,
                    run_metadata,
                    "brand_polish",
                    polished_draft,
                    topic_id=topic.id,
                    draft_id=draft_id,
                    warnings=warnings,
                    provider_warnings=provider_warning_messages,
                )
            except Exception as exc:
                warnings.append(f"brand_polish_failed: {exc}")
        else:
            warnings.append("brand_polish_skipped: no claim verification data")

        if resume and draft_id is not None:
            draft = get_draft(db, draft_id)
            if draft is None:
                raise RuntimeError(f"Checkpointed draft {draft_id} was not found")
        else:
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
        run_metadata = _checkpoint_weekly_value(
            db,
            run_id,
            run_metadata,
            "draft_saved",
            {"draft_id": str(draft.id)},
            topic_id=topic.id,
            draft_id=draft.id,
            warnings=warnings,
            provider_warnings=provider_warning_messages,
        )

        if not (resume and "social_posts" in checkpoints):
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
                run_metadata = _checkpoint_weekly_value(
                    db,
                    run_id,
                    run_metadata,
                    "social_posts",
                    social_posts.model_dump(mode="json"),
                    topic_id=topic.id,
                    draft_id=draft.id,
                    warnings=warnings,
                    provider_warnings=provider_warning_messages,
                )
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
            if resume and "publish_judgment" in checkpoints:
                judgment = PublishJudgmentOutput.model_validate(checkpoints["publish_judgment"])
            elif verification_failed:
                raise RuntimeError("skipped because claim verification failed")
            else:
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
                run_metadata = _checkpoint_weekly_model(
                    db,
                    run_id,
                    run_metadata,
                    "publish_judgment",
                    judgment,
                    topic_id=topic.id,
                    draft_id=draft.id,
                    warnings=warnings,
                    provider_warnings=provider_warning_messages,
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
        mark_run_completed(
            db,
            run_id,
            metadata_json=_weekly_result_metadata(run_metadata, result.model_dump(mode="json")),
        )
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
            metadata_json=_weekly_result_metadata(run_metadata, result.model_dump(mode="json")),
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


def _weekly_checkpoints(metadata: dict[str, Any]) -> dict[str, Any]:
    checkpoints = metadata.get(WEEKLY_CHECKPOINTS_KEY)
    return checkpoints if isinstance(checkpoints, dict) else {}


def _metadata_uuid(metadata: dict[str, Any], key: str) -> UUID | None:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _checkpoint_weekly_model(
    db: Session,
    run_id: UUID,
    metadata: dict[str, Any],
    stage: str,
    value: Any,
    *,
    topic_id: UUID | None,
    draft_id: UUID | None,
    warnings: list[str],
    provider_warnings: list[str],
) -> dict[str, Any]:
    return _checkpoint_weekly_value(
        db,
        run_id,
        metadata,
        stage,
        value.model_dump(mode="json"),
        topic_id=topic_id,
        draft_id=draft_id,
        warnings=warnings,
        provider_warnings=provider_warnings,
    )


def _checkpoint_weekly_value(
    db: Session,
    run_id: UUID,
    metadata: dict[str, Any],
    stage: str,
    value: Any,
    *,
    topic_id: UUID | None,
    draft_id: UUID | None,
    warnings: list[str],
    provider_warnings: list[str],
) -> dict[str, Any]:
    next_metadata = _weekly_result_metadata(
        metadata,
        {
            "topic_id": str(topic_id) if topic_id is not None else None,
            "draft_id": str(draft_id) if draft_id is not None else None,
            "warnings": list(warnings),
            "provider_warnings": list(provider_warnings),
            "resume_stage": stage,
        },
    )
    checkpoints = dict(_weekly_checkpoints(next_metadata))
    checkpoints[stage] = value
    next_metadata[WEEKLY_CHECKPOINTS_KEY] = checkpoints
    next_metadata["completed_stages"] = list(checkpoints.keys())
    next_metadata["resume_stage"] = stage
    update_run_metadata(db, run_id, next_metadata)
    return next_metadata


def _weekly_result_metadata(
    existing_metadata: dict[str, Any],
    result_metadata: dict[str, Any],
) -> dict[str, Any]:
    next_metadata = dict(existing_metadata)
    next_metadata.update(result_metadata)
    return next_metadata
