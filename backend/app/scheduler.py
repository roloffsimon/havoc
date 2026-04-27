"""
Scheduled jobs — one depletion step per day, plus a weekly archive
volume on Monday mornings.

APScheduler runs alongside the FastAPI process. On Railway, this is
the simplest topology that still lets the site update without a
separate worker. Both jobs are idempotent: the daily step is skipped
if the day is already recorded; the weekly volume overwrites the
file for the same ISO week if it already exists.
"""

from __future__ import annotations

import logging
import os
from datetime import date as _date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, depletion, gfw_client, pdf_builder

if TYPE_CHECKING:
    from .ocean_pool import OceanPool

log = logging.getLogger(__name__)

# Daily — shortly after GFW's publication cadence (~midday UTC).
DAILY_HOUR_UTC = int(os.environ.get("HAVOC_SCHEDULE_HOUR_UTC", "14"))
DAILY_MINUTE_UTC = int(os.environ.get("HAVOC_SCHEDULE_MINUTE_UTC", "15"))

# Weekly — Monday morning, after the daily for Sunday has already run.
WEEKLY_HOUR_UTC = int(os.environ.get("HAVOC_WEEKLY_HOUR_UTC", "16"))
WEEKLY_MINUTE_UTC = int(os.environ.get("HAVOC_WEEKLY_MINUTE_UTC", "30"))


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


def make_weekly_job() -> Callable[[], None]:
    """Render the previous Mon–Sun volume; overwrites if already present."""
    def _job():
        today = _date.today()
        # Most recent Sunday on or before today. If today IS Sunday we'd
        # render this week — but the cron is fixed to Mondays, so today
        # is always one day past the week we want.
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday or 7)
        try:
            path = pdf_builder.render_weekly_pdf(last_sunday)
            if path:
                log.info("Weekly volume rendered to %s", path)
            else:
                log.info("Week ending %s had no recorded days — skipped.",
                         last_sunday)
        except Exception as exc:  # noqa: BLE001
            log.exception("Weekly volume failed: %s", exc)
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

    scheduler.add_job(
        make_weekly_job(),
        CronTrigger(day_of_week="mon",
                    hour=WEEKLY_HOUR_UTC, minute=WEEKLY_MINUTE_UTC,
                    timezone="UTC"),
        id="weekly-volume",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    log.info("Scheduled weekly volume at Mon %02d:%02d UTC",
             WEEKLY_HOUR_UTC, WEEKLY_MINUTE_UTC)
