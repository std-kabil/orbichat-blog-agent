from typing import Any

from jobs.celery_app import celery_app
from jobs.placeholders import run_placeholder_workflow


@celery_app.task(name="jobs.weekly_blog_generation.weekly_blog_generation")  # type: ignore[untyped-decorator]
def weekly_blog_generation(run_id: str | None = None) -> dict[str, Any]:
    return run_placeholder_workflow(run_id, "weekly_blog_generation")
