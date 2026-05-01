import sys

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from api.routes_costs import router as costs_router
from api.routes_drafts import router as drafts_router
from api.routes_health import router as health_router
from api.routes_runs import router as runs_router
from api.routes_topics import router as topics_router
from app.config import Settings, get_settings
from app.dependencies import require_admin_api_key


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    if app_settings.sentry_dsn and app_settings.app_env != "test" and "pytest" not in sys.modules:
        sentry_sdk.init(
            dsn=app_settings.sentry_dsn,
            environment=app_settings.app_env,
            traces_sample_rate=0.1,
        )

    app = FastAPI(title=app_settings.app_name)
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    admin_dependencies = [Depends(require_admin_api_key)]
    app.include_router(runs_router, dependencies=admin_dependencies)
    app.include_router(topics_router, dependencies=admin_dependencies)
    app.include_router(drafts_router, dependencies=admin_dependencies)
    app.include_router(costs_router, dependencies=admin_dependencies)

    return app


app = create_app()
