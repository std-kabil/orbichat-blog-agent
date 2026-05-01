import asyncio
from typing import Any
from uuid import UUID

from agents.orchestrator import run_daily_trend_scan
from app.config import get_settings
from app.db import SessionLocal
from jobs.celery_app import celery_app
from repositories.runs import create_run
from schemas.common import RunType


@celery_app.task(name="jobs.daily_trend_scan.daily_trend_scan")  # type: ignore[untyped-decorator]
def daily_trend_scan(run_id: str | None = None) -> dict[str, Any]:
    db = SessionLocal()
    try:
        parsed_run_id = UUID(run_id) if run_id is not None else create_run(db, RunType.DAILY_SCAN).id
        result = asyncio.run(
            run_daily_trend_scan(
                settings=get_settings(),
                db=db,
                run_id=parsed_run_id,
            )
        )
        return result.model_dump(mode="json")
    finally:
        db.close()
