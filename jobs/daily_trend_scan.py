from typing import Any

from jobs.celery_app import celery_app


@celery_app.task(name="jobs.daily_trend_scan.daily_trend_scan")  # type: ignore[untyped-decorator]
def daily_trend_scan(run_id: str | None = None) -> dict[str, Any]:
    return {
        "status": "placeholder",
        "run_id": run_id,
        "workflow": "daily_trend_scan",
        "message": "Phase 1 placeholder task. No external APIs were called.",
    }
