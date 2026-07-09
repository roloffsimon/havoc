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

# Daily data pull — 06:00 Europe/Berlin (local German time). Timezone-
# aware via CronTrigger so it stays 06:00 wall-clock across the CET/CEST
# DST switch (= 05:00 UTC in winter, 04:00 UTC in summer) instead of
# drifting an hour twice a year. GFW's window is always ~3 days old
# (gfw_client.last_available_window), so an early-morning slot has data
# regardless of GFW's own publish cadence.
DAILY_TZ = os.environ.get("HAVOC_SCHEDULE_TZ", "Europe/Berlin")
DAILY_HOUR = int(os.environ.get("HAVOC_SCHEDULE_HOUR", "6"))
DAILY_MINUTE = int(os.environ.get("HAVOC_SCHEDULE_MINUTE", "0"))

# Hard cap on the daily render. Measured runtime ~50s on a 500k-catch
# day; 600s is 12× that — anything past it is a genuine hang and we'd
# rather kill the subprocess than let it pile up against tomorrow's run.
SUBPROCESS_TIMEOUT_S = 600


def _already_processed(date: str) -> bool:
    day = db.latest_day()
    return bool(day and day.get("date") == date)


def _spawn(lang: str, date: str | None = None,
           skip_pdf: bool = False) -> int | None:
    """Run one pass of `scripts.run_daily` as a subprocess. With `date`
    the pass is a re-render from persisted catches; with `skip_pdf` the
    subprocess env gets HAVOC_PDF_SKIP=1 (record_day still runs, no
    typst). Returns the subprocess exit code, or None on launch error /
    timeout (already logged)."""
    cmd = [sys.executable, "-m", "scripts.run_daily", "--lang", lang]
    if date:
        cmd += ["--date", date]
    env = None
    if skip_pdf:
        env = {**os.environ, "HAVOC_PDF_SKIP": "1"}
    log.info("Spawning subprocess: %s%s", " ".join(cmd),
             " (HAVOC_PDF_SKIP=1)" if skip_pdf else "")
    try:
        result = subprocess.run(
            cmd,
            timeout=SUBPROCESS_TIMEOUT_S,
            check=False,
            env=env,
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


def make_job(reload_pool: Callable[[], None]) -> Callable[[], dict]:
    """Return the scheduled callable — THREE minimal-peak subprocesses.

    The original two-pass split (EN = events+persist+render inline,
    DE = re-render) still OOM-killed on heavy days (2026-07-09: rc -9
    after ~60 s, twice): one process holding the 648 MB pool mask, the
    ~1 GB catch buffers AND the typst Rust heap crosses the container
    ceiling. So the render is peeled off the persist entirely:

      Pass 0  --lang en, HAVOC_PDF_SKIP=1 — GFW fetch, pool fold,
              record_day. No typst, peak ≈ mask + catch buffers.
      Pass 1  --lang en --date <day> — EN re-render from the persisted
              catches. No pool mask, no GFW; typst gets the process
              almost to itself. Also refreshes days.pdf_path.
      Pass 2  --lang de --date <day> — DE ditto.

    Passes 1/2 are exactly the re-render path that demonstrably coped
    with the heavy June volumes. Each pass exits before the next starts,
    so the Rust heap never coexists with the pool mask. Returns a result
    dict (the debug trigger endpoint surfaces it; the cron ignores it)."""
    def _job() -> dict:
        # Pre-check in the worker, not the subprocess: lets us skip the
        # ~1-2s of subprocess Python boot when the day is already done.
        # The subprocess does its own check too as a defensive duplicate.
        start, _ = gfw_client.last_available_window()
        if _already_processed(start):
            log.info("Day %s already processed — skipping.", start)
            return {"ok": True, "skipped": True, "date": start}

        runs: list[dict] = []

        # Pass 0: events + pool + DB persist (no render)
        rc = _spawn("en", skip_pdf=True)
        runs.append({"pass": "persist", "rc": rc})
        if rc != 0:
            log.error("Persist pass failed (rc=%s); aborting day", rc)
            return {"ok": False, "runs": runs}
        log.info("Persist pass done; reloading pool")
        try:
            reload_pool()
        except Exception as exc:  # noqa: BLE001
            log.exception("Pool reload after persist pass failed: %s", exc)

        day = db.latest_day()
        if not day or day.get("date") != start:
            log.error("Persist pass exited 0 but day %s is not the latest "
                      "row (%s) — not rendering", start,
                      day.get("date") if day else None)
            return {"ok": False, "runs": runs, "note": "day not recorded"}
        if not day.get("stanzas_caught"):
            log.info("Day %s recorded with 0 catches — nothing to render",
                     start)
            return {"ok": True, "runs": runs, "note": "empty day, no render"}

        # Pass 1 + 2: language renders from the persisted catches
        for lang in ("en", "de"):
            rc = _spawn(lang, date=start)
            runs.append({"pass": f"render-{lang}", "rc": rc})
            if rc != 0:
                log.warning("%s render failed (rc=%s)", lang.upper(), rc)

        return {"ok": all(r["rc"] == 0 for r in runs), "date": start,
                "runs": runs}
    return _job


def attach(scheduler: AsyncIOScheduler, daily: Callable[[], None]) -> None:
    scheduler.add_job(
        daily,
        CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE, timezone=DAILY_TZ),
        id="daily-depletion",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    log.info("Scheduled daily depletion at %02d:%02d %s",
             DAILY_HOUR, DAILY_MINUTE, DAILY_TZ)
