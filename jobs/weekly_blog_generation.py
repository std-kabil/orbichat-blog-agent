from typing import Any

from jobs.celery_app import celery_app


@celery_app.task(name="jobs.weekly_blog_generation.weekly_blog_generation")  # type: ignore[untyped-decorator]
def weekly_blog_generation(run_id: str | None = None) -> dict[str, Any]:
    return {
        "status": "placeholder",
        "run_id": run_id,
        "workflow": "weekly_blog_generation",
        "message": "Phase 1 placeholder task. No external APIs were called.",
    }
