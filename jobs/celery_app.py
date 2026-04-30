from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "orbichat_blog_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "jobs.daily_trend_scan",
        "jobs.weekly_blog_generation",
        "jobs.analytics_sync",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "daily-trend-scan": {
            "task": "jobs.daily_trend_scan.daily_trend_scan",
            "schedule": crontab(hour=9, minute=0),
        },
        "weekly-blog-generation": {
            "task": "jobs.weekly_blog_generation.weekly_blog_generation",
            "schedule": crontab(hour=10, minute=0, day_of_week="mon"),
        },
        "daily-analytics-sync": {
            "task": "jobs.analytics_sync.analytics_sync",
            "schedule": crontab(hour=11, minute=0),
        },
    },
)
