import asyncio
from typing import Any
from uuid import UUID

from agents.orchestrator import run_weekly_blog_generation
from app.config import get_settings
from app.db import SessionLocal
from jobs.celery_app import celery_app


@celery_app.task(name="jobs.weekly_blog_generation.weekly_blog_generation")  # type: ignore[untyped-decorator]
def weekly_blog_generation(run_id: str | None = None) -> dict[str, Any]:
    if run_id is None:
        raise ValueError("run_id is required for weekly blog generation")

    db = SessionLocal()
    try:
        result = asyncio.run(
            run_weekly_blog_generation(
                settings=get_settings(),
                db=db,
                run_id=UUID(run_id),
            )
        )
        return result.model_dump(mode="json")
    finally:
        db.close()
