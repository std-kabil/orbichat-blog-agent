from typing import Any

from jobs.celery_app import celery_app


@celery_app.task(name="jobs.analytics_sync.analytics_sync")  # type: ignore[untyped-decorator]
def analytics_sync(run_id: str | None = None) -> dict[str, Any]:
    return {
        "status": "placeholder",
        "run_id": run_id,
        "workflow": "analytics_sync",
        "message": "Phase 1 placeholder task. No external APIs were called.",
    }
