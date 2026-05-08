"""
Scheduled jobs — one depletion step per day.

The depletion + render runs in TWO subprocess passes (one per language),
not inline in the FastAPI process. Two reasons:

1. typst.compile()'s Rust allocator never returns slabs to the OS, so
   an in-process daily render leaks ~5 GB per day and OOM-kills the
   container on day 2. A subprocess gets a full reclaim on exit.

2. Even within a single subprocess, six tier compiles (3 tiers × 2
   languages) accumulate Rust-heap fragments. On a 646k-catch day
   (2026-05-04) one process holding all six pushed past 7 GB and got
   SIGKILLed by the kernel. Splitting the languages into separate
   subprocess invocations means each only does 3 compiles and peaks
   around 4 GB.

Pass 1 (`--lang en`) is the canonical daily: load pool, fetch GFW
events, mutate the pool, persist DB + new mask, render EN PDFs.

Pass 2 (`--lang de`) is a re-render only: it reads the latest day's
catches from the DB and renders DE PDFs. No GFW, no pool mutation.

After Pass 1 we reload the worker's in-memory pool regardless of how
Pass 2 went — Pass 1 already changed the truth on disk.

Subprocess and web worker share state only through `/data`
(SQLite WAL + pool_mask.bin), which supports concurrent multi-process
access.
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


def _spawn(lang: str) -> int | None:
    """Run one pass of `scripts.run_daily --lang <lang>` as a subprocess.
    Returns the subprocess exit code, or None on launch error / timeout
    (already logged)."""
    cmd = [sys.executable, "-m", "scripts.run_daily", "--lang", lang]
    log.info("Spawning subprocess: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            timeout=SUBPROCESS_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.exception("Subprocess (lang=%s) timed out after %ds",
                      lang, SUBPROCESS_TIMEOUT_S)
        return None
    except Exception as exc:  # noqa: BLE001
        log.exception("Subprocess (lang=%s) failed to launch: %s", lang, exc)
        return None
    if result.returncode != 0:
        log.error("Subprocess (lang=%s) exited %d", lang, result.returncode)
    return result.returncode


def make_job(reload_pool: Callable[[], None]) -> Callable[[], None]:
    """Return the scheduled callable. Runs the EN pass, reloads the pool
    (Pass 1 already mutated /data, so the worker should refresh even if
    the DE pass later fails), then runs the DE pass."""
    def _job():
        # Pre-check in the worker, not the subprocess: lets us skip the
        # ~1-2s of subprocess Python boot when the day is already done.
        # The subprocess does its own check too as a defensive duplicate.
        start, _ = gfw_client.last_available_window()
        if _already_processed(start):
            log.info("Day %s already processed — skipping.", start)
            return

        # Pass 1: events + DB persist + EN render
        en_rc = _spawn("en")
        if en_rc == 0:
            log.info("EN pass completed cleanly; reloading pool")
            try:
                reload_pool()
            except Exception as exc:  # noqa: BLE001
                log.exception("Pool reload after EN pass failed: %s", exc)
        else:
            log.error("EN pass did not complete cleanly; skipping DE pass")
            return

        # Pass 2: DE re-render from the day Pass 1 just persisted
        de_rc = _spawn("de")
        if de_rc != 0:
            log.warning("DE pass failed (rc=%s); EN PDFs are in /data/pdfs",
                        de_rc)
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
