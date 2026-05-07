"""
Daily depletion job — run as a subprocess so the typst Rust heap is
reclaimed by the OS on exit.

Why a subprocess
----------------
typst.compile() accumulates Rust-side heap allocations that don't return
to the OS even after Python objects are gc'd. Running daily renders in
the long-lived web worker means each run inflates RSS by ~3 GB and the
allocations stay around forever; over ~2 days the worker hits Railway's
8 GB ceiling and OOM-kills mid-render. By running each day's render in
its own subprocess we get a guaranteed full reclaim on exit.

Usage
-----
    python -m scripts.run_daily

Reads config from environment (the same vars the web worker uses):
    DATA_DIR              — volume mount point with pool_mask.bin + sqlite
    GFW_TOKEN             — Global Fishing Watch API bearer token
    HAVOC_DAY_0           — project start date (default 2026-02-13)
    HAVOC_FALLBACK_JSON   — optional GFW dump path used if the live API fails
    HAVOC_PDF_ENGINE      — "typst" (default in production) or "weasy"

Exit codes
----------
    0   day rendered, or already processed (idempotent skip)
    1   depletion run raised an exception (logged with traceback)
    2   pool mask missing on disk — pool not bootstrapped
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Run the same way init_pool does, so `python scripts/run_daily.py` and
# `python -m scripts.run_daily` are both valid.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # fontTools is chatty during typst font subsetting — pin it down so
    # the subprocess log stays readable.
    for noisy in ("fontTools", "fontTools.subset", "fontTools.ttLib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    log = logging.getLogger("scripts.run_daily")

    # Late imports so any import failure in app.* shows up in the
    # subprocess log, not at module-collect time.
    from app import db, depletion, gfw_client
    from app.ocean_pool import OceanPool

    # 1. Load pool from disk
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

    # 2. Idempotency — defensive duplicate of the worker's pre-check, in
    # case the subprocess gets invoked manually or via cron-misfire.
    start, _ = gfw_client.last_available_window()
    last_day = db.latest_day()
    if last_day and last_day.get("date") == start:
        log.info("Day %s already processed — skipping.", start)
        return 0

    # 3. Run depletion + render PDFs + persist
    project_day_0 = os.environ.get("HAVOC_DAY_0", "2026-02-13")
    fallback_env = os.environ.get("HAVOC_FALLBACK_JSON")
    fallback_path = Path(fallback_env) if fallback_env else None
    if fallback_path and not fallback_path.exists():
        fallback_path = None
    try:
        depletion.run_latest(pool, project_day_0, fallback_json=fallback_path)
    except Exception as exc:  # noqa: BLE001
        log.exception("Daily depletion failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
