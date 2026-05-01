from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_database_session
from app.main import create_app
from schemas.common import TopicStatus
from schemas.cost import CostSummary

ADMIN_API_KEY = "test-admin-secret"


def _client() -> TestClient:
    app = create_app(Settings(app_env="test", sentry_dsn=None, admin_api_key=ADMIN_API_KEY))
    app.dependency_overrides[get_database_session] = lambda: object()
    return TestClient(app)


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_API_KEY}"}


def _run(status: str = "queued") -> SimpleNamespace:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid4(),
        run_type="daily_scan",
        status=status,
        started_at=None,
        finished_at=None,
        total_cost_usd=Decimal("0"),
        total_input_tokens=0,
        total_output_tokens=0,
        error_message=None,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


def _topic(status: str = "candidate") -> SimpleNamespace:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid4(),
        run_id=None,
        title="Topic",
        target_keyword=None,
        search_intent=None,
        summary=None,
        trend_score=0,
        orbichat_relevance_score=0,
        seo_score=0,
        conversion_score=0,
        total_score=0,
        recommended=False,
        reasoning=None,
        cta_angle=None,
        status=status,
        created_at=now,
        updated_at=now,
    )


def _draft() -> SimpleNamespace:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid4(),
        topic_id=uuid4(),
        title="Draft",
        slug="draft",
        meta_title=None,
        meta_description=None,
        target_keyword=None,
        markdown_content="# Draft",
        outline_json={},
        seo_json={},
        status="draft",
        version=1,
        publish_score=None,
        publish_ready=False,
        payload_post_id=None,
        created_at=now,
        updated_at=now,
    )


def test_get_run_returns_not_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("api.routes_runs.get_run", lambda db, run_id: None)

    response = _client().get(f"/runs/{uuid4()}", headers=_admin_headers())

    assert response.status_code == 404


def test_get_run_returns_run(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run = _run()
    monkeypatch.setattr("api.routes_runs.get_run", lambda db, run_id: run)

    response = _client().get(f"/runs/{run.id}", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()["id"] == str(run.id)


def test_topic_approve_updates_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_update(db: object, topic_id: object, status: TopicStatus) -> SimpleNamespace:
        return _topic(status=status.value)

    monkeypatch.setattr("api.routes_topics.update_topic_status", fake_update)

    response = _client().post(f"/topics/{uuid4()}/approve", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_draft_list_returns_drafts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    draft = _draft()
    monkeypatch.setattr("api.routes_drafts.list_drafts_repo", lambda db, limit: [draft])

    response = _client().get("/drafts", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(draft.id)


def test_cost_summary_returns_zeroes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "api.routes_costs.summarize_costs",
        lambda db: CostSummary(
            run_id=None,
            total_estimated_cost_usd=Decimal("0"),
            total_input_tokens=0,
            total_output_tokens=0,
            llm_call_count=0,
            search_call_count=0,
            model_usage=[],
        ),
    )

    response = _client().get("/costs/summary", headers=_admin_headers())

    assert response.status_code == 200
    assert response.json()["total_estimated_cost_usd"] == "0"


def test_health_routes_do_not_require_admin_auth() -> None:
    response = _client().get("/health")

    assert response.status_code == 200


def test_admin_routes_reject_missing_credentials() -> None:
    response = _client().get("/runs")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_admin_routes_reject_invalid_credentials() -> None:
    response = _client().get("/runs", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 403


def test_admin_routes_accept_x_admin_api_key_header(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("api.routes_runs.list_runs_repo", lambda db, limit: [])

    response = _client().get("/runs", headers={"X-Admin-API-Key": ADMIN_API_KEY})

    assert response.status_code == 200


def test_admin_routes_fail_closed_when_auth_is_not_configured() -> None:
    app = create_app(Settings(app_env="test", sentry_dsn=None))
    app.dependency_overrides[get_database_session] = lambda: object()

    response = TestClient(app).get("/runs", headers=_admin_headers())

    assert response.status_code == 503
