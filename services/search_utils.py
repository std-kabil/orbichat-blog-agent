from datetime import datetime
from typing import Any

import httpx


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def require_mapping(value: object, provider: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{provider} returned a non-object response")
    return value


def transient_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    return False


def raise_for_status(response: httpx.Response) -> None:
    response.raise_for_status()
