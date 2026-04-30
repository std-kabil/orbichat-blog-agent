from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from schemas.run import RunCreateResponse, RunRead


def test_run_create_response_serializes_uuid() -> None:
    run_id = uuid4()

    response = RunCreateResponse(
        run_id=run_id,
        job_id="celery-job-id",
        run_type="daily_scan",
        status="queued",
    )

    assert response.model_dump(mode="json") == {
        "run_id": str(run_id),
        "job_id": "celery-job-id",
        "run_type": "daily_scan",
        "status": "queued",
    }


def test_run_read_schema_accepts_phase_one_fields() -> None:
    run_id = uuid4()
    created_at = datetime(2026, 4, 30, tzinfo=UTC)

    response = RunRead(
        id=run_id,
        run_type="weekly_blog_generation",
        status="queued",
        started_at=None,
        finished_at=None,
        total_cost_usd=Decimal("0"),
        total_input_tokens=0,
        total_output_tokens=0,
        error_message=None,
        metadata_json={},
        created_at=created_at,
        updated_at=created_at,
    )

    assert response.id == run_id
    assert response.status == "queued"
    assert response.metadata_json == {}
