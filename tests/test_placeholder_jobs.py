from uuid import uuid4

from jobs.placeholders import run_placeholder_workflow


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_placeholder_workflow_updates_run_status(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []
    fake_session = FakeSession()

    monkeypatch.setattr("jobs.placeholders.SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        "jobs.placeholders.mark_run_running",
        lambda db, run_id: calls.append("running"),
    )
    monkeypatch.setattr(
        "jobs.placeholders.mark_run_completed",
        lambda db, run_id, metadata_json: calls.append("completed"),
    )

    result = run_placeholder_workflow(str(uuid4()), "daily_trend_scan")

    assert result["status"] == "completed"
    assert calls == ["running", "completed"]
    assert fake_session.closed is True
