"""
Daily depletion job — run as a subprocess so the typst Rust heap is
reclaimed by the OS on exit.

Why a subprocess
----------------
typst.compile() accumulates Rust-side heap allocations that don't return
to the OS even after Python objects are gc'd. Running daily renders in
the long-lived web worker leaks ~5 GB per day; over ~2 days the worker
hits Railway's 8 GB ceiling and OOM-kills mid-render. A subprocess
gets a guaranteed full reclaim on its exit.

Why one subprocess per language
-------------------------------
Even within a single subprocess, six tier compiles in sequence (3 tiers
× 2 languages) accumulate Rust-heap fragments and on heavy days
(>600k catches) push the subprocess past 7 GB. Running EN and DE in
separate subprocess invocations means each only does 3 compiles and
peaks around 4 GB.

Two modes:

    python -m scripts.run_daily --lang en
        Standard daily run. Loads pool, fetches GFW events, processes
        them, writes the day to the DB, persists the new pool mask,
        and renders the EN PDFs.

    python -m scripts.run_daily --lang de
        Re-render only. Reads the most recently recorded day from the
        DB and renders the DE PDFs from those persisted catches —
        no GFW fetch, no pool mutation. Should be invoked AFTER the
        --lang en run so the latest day's catches are in the DB.

Env (same vars as the web worker):
    DATA_DIR / GFW_TOKEN / HAVOC_DAY_0 / HAVOC_FALLBACK_JSON / HAVOC_PDF_ENGINE

Exit codes:
    0   day rendered, or already processed (idempotent skip)
    1   render failed (logged with traceback)
    2   pool mask missing / no day to re-render
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Match scripts.init_pool: keep the sys.path tweak so direct invocation
# (`python scripts/run_daily.py …`) works alongside the standard
# `python -m scripts.run_daily` form.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # fontTools is chatty during typst font subsetting — pin it down so
    # the subprocess log stays readable.
    for noisy in ("fontTools", "fontTools.subset", "fontTools.ttLib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("scripts.run_daily")


def _run_en(log: logging.Logger) -> int:
    """Standard daily pass: events + DB persist + EN render."""
    from app import db, depletion, gfw_client
    from app.ocean_pool import OceanPool

    db.init_db()
    mask = db.load_mask()
    if mask is None:
        log.error("No pool mask at %s — cannot run daily job", db.MASK_PATH)
        return 2

    state = db.load_pool_state() or {"cursor": 0, "direction": 1, "catch_count": 0}
    pool = OceanPool(mask, cursor=state["cursor"], direction=state["direction"])
    pool.catch_count = int(state.get("catch_count", 0))
    alive_now = int(pool.mask.sum())
    pool.water_cells = alive_now + pool.catch_count
    log.info("Pool loaded: %s alive / %s total (catches=%s)",
             f"{pool.remaining:,}", f"{pool.water_cells:,}", f"{pool.catch_count:,}")

    # Defensive duplicate of the worker's pre-check.
    start, _ = gfw_client.last_available_window()
    last_day = db.latest_day()
    if last_day and last_day.get("date") == start:
        log.info("Day %s already processed — skipping.", start)
        return 0

    project_day_0 = os.environ.get("HAVOC_DAY_0", "2026-02-13")
    fallback_env = os.environ.get("HAVOC_FALLBACK_JSON")
    fallback_path = Path(fallback_env) if fallback_env else None
    if fallback_path and not fallback_path.exists():
        fallback_path = None
    try:
        depletion.run_latest(pool, project_day_0,
                             fallback_json=fallback_path,
                             languages=("en",))
    except Exception as exc:  # noqa: BLE001
        log.exception("Daily depletion (en) failed: %s", exc)
        return 1
    return 0


def _run_de(log: logging.Logger) -> int:
    """Re-render only: read latest day from DB, render DE PDFs."""
    from app import db, pdf_builder

    db.init_db()
    latest = db.latest_day()
    if not latest:
        log.error("No recorded day in DB — cannot render DE")
        return 2
    date = latest["date"]
    log.info("Re-rendering DE for %s", date)
    try:
        result = pdf_builder.render_persisted_day(date, language="de")
    except Exception as exc:  # noqa: BLE001
        log.exception("DE re-render failed: %s", exc)
        return 1
    if result is None:
        log.error("render_persisted_day returned None for %s", date)
        return 1
    return 0


def main() -> int:
    log = _setup_logging()
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--lang", choices=("en", "de"), default="en",
                    help="Which language pass to run (default: en)")
    args = ap.parse_args()
    if args.lang == "en":
        return _run_en(log)
    return _run_de(log)


if __name__ == "__main__":
    sys.exit(main())
