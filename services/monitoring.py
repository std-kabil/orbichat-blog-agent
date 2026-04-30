from uuid import UUID

from loguru import logger
import sentry_sdk

from app.config import Settings


def log_run_event(
    *,
    event: str,
    run_id: UUID | None = None,
    topic_id: UUID | None = None,
    draft_id: UUID | None = None,
    task_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    message: str | None = None,
) -> None:
    bound_logger = logger.bind(
        run_id=str(run_id) if run_id else None,
        topic_id=str(topic_id) if topic_id else None,
        draft_id=str(draft_id) if draft_id else None,
        task_name=task_name,
        provider=provider,
        model=model,
        status=status,
        event=event,
    )
    if status == "failed":
        bound_logger.error(message or event)
    elif status in {"warning", "budget_blocked"}:
        bound_logger.warning(message or event)
    else:
        bound_logger.info(message or event)


def capture_run_exception(
    *,
    settings: Settings,
    exc: Exception,
    run_id: UUID | None = None,
    topic_id: UUID | None = None,
    draft_id: UUID | None = None,
    task_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    if not settings.sentry_dsn or settings.app_env == "test":
        return

    with sentry_sdk.push_scope() as scope:
        if run_id is not None:
            scope.set_tag("run_id", str(run_id))
        if topic_id is not None:
            scope.set_tag("topic_id", str(topic_id))
        if draft_id is not None:
            scope.set_tag("draft_id", str(draft_id))
        if task_name is not None:
            scope.set_tag("task_name", task_name)
        if provider is not None:
            scope.set_tag("provider", provider)
        if model is not None:
            scope.set_tag("model", model)
        sentry_sdk.capture_exception(exc)
