from uuid import UUID

from sqlalchemy.orm import Session

from agents.topic_scorer import score_and_store_topics
from agents.trend_discovery import (
    TrendSearchRouter,
    dedupe_trend_candidates,
    discover_trend_candidates,
    group_topic_candidates,
)
from app.config import Settings
from repositories.costs import summarize_costs
from repositories.runs import mark_run_completed, mark_run_failed, mark_run_running, update_run_totals
from schemas.trend import DailyTrendScanResult


async def run_daily_trend_scan(
    *,
    settings: Settings,
    db: Session,
    run_id: UUID,
    search_router: TrendSearchRouter | None = None,
) -> DailyTrendScanResult:
    mark_run_running(db, run_id)

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
        return result
    except Exception as exc:
        mark_run_failed(db, run_id, str(exc))
        raise
