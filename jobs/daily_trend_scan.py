from typing import Any

from jobs.celery_app import celery_app
from jobs.placeholders import run_placeholder_workflow


@celery_app.task(name="jobs.daily_trend_scan.daily_trend_scan")  # type: ignore[untyped-decorator]
def daily_trend_scan(run_id: str | None = None) -> dict[str, Any]:
    return run_placeholder_workflow(run_id, "daily_trend_scan")
