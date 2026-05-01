from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.errors import not_found
from jobs.daily_trend_scan import daily_trend_scan
from jobs.weekly_blog_generation import weekly_blog_generation
from repositories.runs import create_run, get_run, list_runs as list_runs_repo, mark_run_queued
from schemas.common import RunStatus, RunType
from schemas.run import RunCreateResponse, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


def enqueue_run(db: Session, run_type: str) -> RunCreateResponse:
    typed_run_type = RunType(run_type)
    run = create_run(db, typed_run_type)

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


@router.post(
    "/{run_id}/resume",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resume_run(
    run_id: UUID,
    db: Session = Depends(get_database_session),
) -> RunCreateResponse:
    run = get_run(db, run_id)
    if run is None:
        raise not_found("Run not found")
    if run.status != RunStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed runs can be resumed.",
        )
    if run.run_type not in {RunType.WEEKLY_BLOG_GENERATION.value, RunType.MANUAL_DRAFT.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only blog draft generation runs can be resumed.",
        )
    if not run.metadata_json.get("topic_id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run does not have enough checkpoint metadata to resume.",
        )

    queued_run = mark_run_queued(db, run.id) or run
    task = weekly_blog_generation.delay(str(run.id), True)
    return RunCreateResponse(
        run_id=queued_run.id,
        job_id=task.id,
        run_type=RunType(queued_run.run_type),
        status=RunStatus(queued_run.status),
    )


@router.get("", response_model=list[RunRead])
def list_runs(
    db: Session = Depends(get_database_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RunRead]:
    runs = list_runs_repo(db, limit=limit)
    return [RunRead.model_validate(run) for run in runs]


@router.get("/{run_id}", response_model=RunRead)
def read_run(
    run_id: UUID,
    db: Session = Depends(get_database_session),
) -> RunRead:
    run = get_run(db, run_id)
    if run is None:
        raise not_found("Run not found")
    return RunRead.model_validate(run)
