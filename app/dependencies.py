from collections.abc import Generator
from hmac import compare_digest

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db


def get_database_session() -> Generator[Session, None, None]:
    yield from get_db()


def require_admin_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> None:
    settings = request.app.state.settings
    configured_key = settings.admin_api_key.get_secret_value() if settings.admin_api_key else None
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured",
        )

    provided_key = _extract_admin_api_key(
        authorization=authorization,
        x_admin_api_key=x_admin_api_key,
    )
    if provided_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not compare_digest(provided_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials",
        )


def _extract_admin_api_key(
    *,
    authorization: str | None,
    x_admin_api_key: str | None,
) -> str | None:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()

    if x_admin_api_key:
        return x_admin_api_key.strip()

    return None
