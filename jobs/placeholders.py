from typing import Any
from uuid import UUID

from app.db import SessionLocal
from repositories.runs import mark_run_completed, mark_run_failed, mark_run_running


def run_placeholder_workflow(run_id: str | None, workflow: str) -> dict[str, Any]:
    if run_id is None:
        return {
            "status": "placeholder",
            "run_id": None,
            "workflow": workflow,
            "message": "Phase 2 placeholder task. No external APIs were called.",
        }

    parsed_run_id = UUID(run_id)
    db = SessionLocal()
    try:
        mark_run_running(db, parsed_run_id)
        metadata = {
            "workflow": workflow,
            "message": "Phase 2 placeholder task. No external APIs were called.",
        }
        mark_run_completed(db, parsed_run_id, metadata_json=metadata)
        return {
            "status": "completed",
            "run_id": run_id,
            "workflow": workflow,
            "message": metadata["message"],
        }
    except Exception as exc:
        mark_run_failed(db, parsed_run_id, str(exc))
        raise
    finally:
        db.close()
