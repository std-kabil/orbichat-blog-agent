from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.models import AgentRun
from jobs.daily_trend_scan import daily_trend_scan
from jobs.weekly_blog_generation import weekly_blog_generation
from schemas.run import RunCreateResponse, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


def enqueue_run(db: Session, run_type: str) -> RunCreateResponse:
    run = AgentRun(run_type=run_type, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)

    task = (
        daily_trend_scan.delay(str(run.id))
        if run_type == "daily_scan"
        else weekly_blog_generation.delay(str(run.id))
    )

    return RunCreateResponse(
        run_id=run.id,
        job_id=task.id,
        run_type=run.run_type,
        status=run.status,
    )


@router.post(
    "/daily-scan",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_daily_scan_run(
    db: Session = Depends(get_database_session),
) -> RunCreateResponse:
    return enqueue_run(db, "daily_scan")


@router.post(
    "/weekly-blog-generation",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_weekly_blog_generation_run(
    db: Session = Depends(get_database_session),
) -> RunCreateResponse:
    return enqueue_run(db, "weekly_blog_generation")


@router.get("", response_model=list[RunRead])
def list_runs(
    db: Session = Depends(get_database_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RunRead]:
    statement = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    runs = db.scalars(statement).all()
    return [RunRead.model_validate(run) for run in runs]
