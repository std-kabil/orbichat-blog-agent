from typing import Any

from jobs.celery_app import celery_app
from jobs.placeholders import run_placeholder_workflow


@celery_app.task(name="jobs.analytics_sync.analytics_sync")  # type: ignore[untyped-decorator]
def analytics_sync(run_id: str | None = None) -> dict[str, Any]:
    return run_placeholder_workflow(run_id, "analytics_sync")
