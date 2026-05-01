import asyncio
from typing import Any
from uuid import UUID

from agents.orchestrator import run_weekly_blog_generation
from app.config import get_settings
from app.db import SessionLocal
from jobs.celery_app import celery_app
from repositories.runs import create_run
from schemas.common import RunType


@celery_app.task(name="jobs.weekly_blog_generation.weekly_blog_generation")  # type: ignore[untyped-decorator]
def weekly_blog_generation(run_id: str | None = None, resume: bool = False) -> dict[str, Any]:
    db = SessionLocal()
    try:
        parsed_run_id = (
            UUID(run_id) if run_id is not None else create_run(db, RunType.WEEKLY_BLOG_GENERATION).id
        )
        result = asyncio.run(
            run_weekly_blog_generation(
                settings=get_settings(),
                db=db,
                run_id=parsed_run_id,
                resume=resume,
            )
        )
        return result.model_dump(mode="json")
    finally:
        db.close()
