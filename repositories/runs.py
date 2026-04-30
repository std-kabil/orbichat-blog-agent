from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun
from schemas.common import RunStatus, RunType
from schemas.cost import CostSummary


def create_run(db: Session, run_type: RunType) -> AgentRun:
    run = AgentRun(run_type=run_type.value, status=RunStatus.QUEUED.value)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, limit: int = 50) -> list[AgentRun]:
    statement = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_run(db: Session, run_id: UUID) -> AgentRun | None:
    return db.get(AgentRun, run_id)


def mark_run_running(db: Session, run_id: UUID) -> AgentRun | None:
    run = get_run(db, run_id)
    if run is None:
        return None

    now = datetime.now(UTC)
    run.status = RunStatus.RUNNING.value
    run.started_at = now
    run.updated_at = now
    db.commit()
    db.refresh(run)
    return run


def mark_run_completed(
    db: Session,
    run_id: UUID,
    metadata_json: dict[str, Any] | None = None,
) -> AgentRun | None:
    run = get_run(db, run_id)
    if run is None:
        return None

    now = datetime.now(UTC)
    run.status = RunStatus.COMPLETED.value
    run.finished_at = now
    run.updated_at = now
    run.error_message = None
    if metadata_json is not None:
        run.metadata_json = metadata_json
    db.commit()
    db.refresh(run)
    return run


def mark_run_failed(db: Session, run_id: UUID, error_message: str) -> AgentRun | None:
    run = get_run(db, run_id)
    if run is None:
        return None

    now = datetime.now(UTC)
    run.status = RunStatus.FAILED.value
    run.finished_at = now
    run.updated_at = now
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def mark_run_failed_with_metadata(
    db: Session,
    run_id: UUID,
    *,
    error_message: str,
    metadata_json: dict[str, Any],
) -> AgentRun | None:
    run = mark_run_failed(db, run_id, error_message)
    if run is None:
        return None

    run.metadata_json = metadata_json
    db.commit()
    db.refresh(run)
    return run


def update_run_totals(db: Session, run_id: UUID, costs: CostSummary) -> AgentRun | None:
    run = get_run(db, run_id)
    if run is None:
        return None

    run.total_cost_usd = costs.total_estimated_cost_usd
    run.total_input_tokens = costs.total_input_tokens
    run.total_output_tokens = costs.total_output_tokens
    db.commit()
    db.refresh(run)
    return run
