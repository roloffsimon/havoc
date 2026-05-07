"""
Scheduled jobs — one depletion step per day.

The depletion + render runs in a subprocess (`scripts.run_daily`), not
inline in the FastAPI process. typst.compile()'s Rust allocator never
returns slabs to the OS, so an in-process daily render leaks ~5 GB per
day and OOM-kills the container on day 2. Spawning a subprocess gives
us a guaranteed full reclaim on its exit. The subprocess and the web
worker share state only through `/data` (SQLite WAL + pool_mask.bin),
both of which support concurrent multi-process access.

After the subprocess exits cleanly we re-read the pool from disk so
`/api/status` and friends reflect the new catch_count without waiting
for a worker restart.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, gfw_client

log = logging.getLogger(__name__)

# Daily — shortly after GFW's publication cadence (~midday UTC).
DAILY_HOUR_UTC = int(os.environ.get("HAVOC_SCHEDULE_HOUR_UTC", "14"))
DAILY_MINUTE_UTC = int(os.environ.get("HAVOC_SCHEDULE_MINUTE_UTC", "15"))

# Hard cap on the daily render. Measured runtime ~50s on a 500k-catch
# day; 600s is 12× that — anything past it is a genuine hang and we'd
# rather kill the subprocess than let it pile up against tomorrow's run.
SUBPROCESS_TIMEOUT_S = 600


def _already_processed(date: str) -> bool:
    day = db.latest_day()
    return bool(day and day.get("date") == date)


def make_job(reload_pool: Callable[[], None]) -> Callable[[], None]:
    """Return the scheduled callable. After a successful subprocess run
    invokes `reload_pool` so the web worker's in-memory OceanPool picks
    up the fresh mask and catch_count from disk."""
    def _job():
        # Pre-check in the worker, not the subprocess: lets us skip the
        # ~1-2s of subprocess Python boot when the day is already done.
        # The subprocess does its own check too as a defensive duplicate.
        start, _ = gfw_client.last_available_window()
        if _already_processed(start):
            log.info("Day %s already processed — skipping.", start)
            return

        cmd = [sys.executable, "-m", "scripts.run_daily"]
        log.info("Spawning daily render subprocess: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                timeout=SUBPROCESS_TIMEOUT_S,
                check=False,  # we handle non-zero exit explicitly
            )
        except subprocess.TimeoutExpired:
            log.exception("Daily render subprocess timed out after %ds",
                          SUBPROCESS_TIMEOUT_S)
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("Daily render subprocess failed to launch: %s", exc)
            return

        if result.returncode != 0:
            log.error("Daily render subprocess exited %d", result.returncode)
            return

        log.info("Daily render subprocess completed cleanly; reloading pool")
        try:
            reload_pool()
        except Exception as exc:  # noqa: BLE001
            log.exception("Pool reload after daily run failed: %s", exc)
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
