from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import settings
from .monitor import MonitorService

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.scheduler_enabled:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    hours = [h.strip() for h in settings.scheduler_hours.split(",") if h.strip()]
    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    service = MonitorService()

    for hour in hours:
        scheduler.add_job(
            service.run_once,
            trigger=CronTrigger(day_of_week="mon-fri", hour=int(hour), minute=settings.scheduler_minute),
            kwargs={"force_agent": True},
            id=f"monitor_{hour}_{settings.scheduler_minute}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
