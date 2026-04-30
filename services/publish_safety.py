from uuid import UUID
from typing import cast

from sqlalchemy.orm import Session

from agents.blog_generation import judge_publish_readiness
from agents.publish_checks import run_deterministic_publish_checks
from app.config import Settings
from app.models import BlogDraft, FactCheck
from repositories.drafts import get_draft, update_publish_metadata, update_safety_metadata
from repositories.fact_checks import list_fact_checks_by_draft
from schemas.common import DraftStatus
from schemas.workflow import (
    BlogDraftOutput,
    ClaimType,
    ClaimVerificationOutput,
    DraftSafetyReport,
    FactCheckSummary,
    RecommendedAction,
    RiskLevel,
    PublishJudgmentOutput,
    VerificationVerdict,
)


async def run_publish_safety_for_draft(
    *,
    settings: Settings,
    db: Session,
    draft_id: UUID,
    run_id: UUID | None = None,
) -> DraftSafetyReport:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise ValueError("Draft not found")

    verifications = [_verification_from_fact_check(fact_check) for fact_check in list_fact_checks_by_draft(db, draft_id)]
    deterministic_checks = run_deterministic_publish_checks(
        settings=settings,
        title=draft.title,
        slug=draft.slug,
        meta_description=draft.meta_description,
        markdown_content=draft.markdown_content,
        verifications=verifications,
    )

    judgment = await judge_publish_readiness(
        settings=settings,
        db=db,
        run_id=run_id or draft.id,
        topic_id=draft.topic_id,
        draft_id=draft.id,
        draft=_draft_output(draft),
        deterministic_blockers=deterministic_checks.blockers,
        verifications=verifications,
    )
    publish_ready = _publish_ready(
        settings=settings,
        deterministic_ready=deterministic_checks.publish_ready,
        judgment=judgment,
    )

    update_publish_metadata(
        db,
        draft_id=draft.id,
        publish_score=judgment.score,
        publish_ready=publish_ready,
        status=DraftStatus.DRAFT,
    )
    metadata = {
        "deterministic_blockers": deterministic_checks.blockers,
        "required_fixes": judgment.required_fixes,
        "reasoning": judgment.reasoning,
        "risk_level": judgment.risk_level,
        "model_publish_ready": judgment.publish_ready,
        "min_publish_score": settings.min_publish_score,
    }
    update_safety_metadata(db, draft_id=draft.id, safety_metadata=metadata)

    return build_safety_report(draft=draft, fact_checks=list_fact_checks_by_draft(db, draft.id))


def build_safety_report(*, draft: BlogDraft, fact_checks: list[FactCheck]) -> DraftSafetyReport:
    metadata = (draft.seo_json or {}).get("publish_safety", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return DraftSafetyReport(
        draft_id=draft.id,
        publish_ready=draft.publish_ready,
        publish_score=draft.publish_score,
        deterministic_blockers=_string_list(metadata.get("deterministic_blockers")),
        required_fixes=_string_list(metadata.get("required_fixes")),
        fact_check_summary=_fact_check_summary(fact_checks),
        reasoning=str(metadata.get("reasoning")) if metadata.get("reasoning") is not None else None,
    )


def _publish_ready(
    *,
    settings: Settings,
    deterministic_ready: bool,
    judgment: PublishJudgmentOutput,
) -> bool:
    return (
        deterministic_ready
        and judgment.publish_ready
        and settings.auto_publish
        and judgment.score >= settings.min_publish_score
    )


def _draft_output(draft: BlogDraft) -> BlogDraftOutput:
    return BlogDraftOutput(
        title=draft.title,
        slug=draft.slug,
        meta_title=draft.meta_title or draft.title,
        meta_description=draft.meta_description or "",
        markdown_content=draft.markdown_content,
        notes="Existing saved draft.",
    )


def _verification_from_fact_check(fact_check: FactCheck) -> ClaimVerificationOutput:
    return ClaimVerificationOutput(
        claim=fact_check.claim,
        claim_type=cast(ClaimType | None, fact_check.claim_type),
        verdict=cast(VerificationVerdict, fact_check.verdict),
        severity=cast(RiskLevel, fact_check.severity),
        explanation=fact_check.explanation or "",
        source_urls=fact_check.source_urls_json,
        recommended_action=cast(RecommendedAction, fact_check.recommended_action or "keep"),
    )


def _fact_check_summary(fact_checks: list[FactCheck]) -> FactCheckSummary:
    return FactCheckSummary(
        total=len(fact_checks),
        supported=sum(1 for item in fact_checks if item.verdict == "supported"),
        unsupported=sum(1 for item in fact_checks if item.verdict == "unsupported"),
        unclear=sum(1 for item in fact_checks if item.verdict == "unclear"),
        opinion=sum(1 for item in fact_checks if item.verdict == "opinion"),
        high_severity_unsupported=sum(
            1 for item in fact_checks if item.verdict == "unsupported" and item.severity == "high"
        ),
        medium_severity_unclear=sum(
            1 for item in fact_checks if item.verdict == "unclear" and item.severity == "medium"
        ),
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
