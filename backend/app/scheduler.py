"""
Scheduled jobs — one depletion step per day.

APScheduler runs alongside the FastAPI process. On Railway, this is
the simplest topology that still lets the site update without a
separate worker. The daily step is idempotent: it's skipped if the
day is already recorded.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, depletion, gfw_client

if TYPE_CHECKING:
    from .ocean_pool import OceanPool

log = logging.getLogger(__name__)

# Daily — shortly after GFW's publication cadence (~midday UTC).
DAILY_HOUR_UTC = int(os.environ.get("HAVOC_SCHEDULE_HOUR_UTC", "14"))
DAILY_MINUTE_UTC = int(os.environ.get("HAVOC_SCHEDULE_MINUTE_UTC", "15"))


def _already_processed(date: str) -> bool:
    day = db.latest_day()
    return bool(day and day.get("date") == date)


def make_job(pool_provider: Callable[[], OceanPool], project_day_0: str,
             fallback_json: Path | None = None) -> Callable[[], None]:
    def _job():
        start, _ = gfw_client.last_available_window()
        if _already_processed(start):
            log.info("Day %s already processed — skipping.", start)
            return
        pool = pool_provider()
        try:
            depletion.run_latest(pool, project_day_0, fallback_json=fallback_json)
        except Exception as exc:  # noqa: BLE001
            log.exception("Daily depletion failed: %s", exc)
    return _job


def attach(scheduler: AsyncIOScheduler, daily: Callable[[], None]) -> None:
    scheduler.add_job(
        daily,
        CronTrigger(hour=DAILY_HOUR_UTC, minute=DAILY_MINUTE_UTC, timezone="UTC"),
        id="daily-depletion",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    log.info("Scheduled daily depletion at %02d:%02d UTC",
             DAILY_HOUR_UTC, DAILY_MINUTE_UTC)
