"""
reset_project.py

One-shot reset: wipe day/catch/vessel/pool tables, drop the cached
depletion bitmap and the persisted pool mask, then re-initialise the
pool from `backend/ocean_mask.npz`. Used when we want to restart
the project on a new day-0 with a freshly generated, display-aligned
mask.

Order matters:
  1. wipe DB rows
  2. unlink mask + bitmap files
  3. call init_pool (which writes a new mask + pool_state row)

After this:
  - `pool_state` has a single row, catch_count = 0
  - `days`, `catches`, `vessels_active` are empty
  - The next daily job runs against a clean pool against the new mask

Usage
-----
    python -m scripts.reset_project [--from backend/ocean_mask.npz]
                                    [--project-day-0 YYYY-MM-DD]

`--from` defaults to `backend/ocean_mask.npz` (the upsampled mask
written by `generation/upsample_to_backend_mask.py`).
`--project-day-0` defaults to today's UTC date.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Match init_pool's path-tweak so `app` and `scripts.init_pool` both
# resolve when invoked as `python -m scripts.reset_project`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.ocean_pool import OceanPool  # noqa: E402

from scripts.init_pool import load_from_npz  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reset_project")


# The mask sits next to the `app/` package, i.e. one level above this
# `scripts/` directory. Same anchor in the dev layout (`backend/`) and
# the production container (`/app/`), where the deploy flattens away
# the `backend/` segment.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASK = BACKEND_ROOT / "ocean_mask.npz"


def wipe_tables() -> None:
    with db.connect() as c:
        # Order matters only nominally — no FKs are enforced — but keep
        # children-before-parents for clarity.
        for table in ("catches", "vessels_active", "days", "pool_state"):
            count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            c.execute(f"DELETE FROM {table}")
            log.info("Cleared %s (%d rows)", table, count)


def drop_files() -> None:
    for path in (db.MASK_PATH, db.DEPLETION_BITMAP_PATH):
        if path.exists():
            path.unlink()
            log.info("Removed %s", path)
        else:
            log.info("Skip (not present): %s", path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", type=Path, default=DEFAULT_MASK,
                    help="Mask .npz to load (default: backend/ocean_mask.npz)")
    ap.add_argument("--project-day-0", type=str, default=None,
                    help="Project day 0 in YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--yes", action="store_true",
                    help="Skip the confirmation prompt")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"Mask not found: {args.src}")

    if not args.yes:
        prompt = ("This wipes catches/days/vessels_active/pool_state, removes the "
                  "pool mask + depletion bitmap, and reinitialises the pool from "
                  f"{args.src}. Type 'reset' to confirm: ")
        if input(prompt).strip() != "reset":
            raise SystemExit("Aborted.")

    day_0 = args.project_day_0 or datetime.now(timezone.utc).date().isoformat()
    try:
        date.fromisoformat(day_0)
    except ValueError as exc:
        raise SystemExit(f"--project-day-0 must be YYYY-MM-DD: {exc}")

    db.init_db()

    wipe_tables()
    drop_files()

    log.info("Loading mask from %s", args.src)
    mask = load_from_npz(args.src)
    pool = OceanPool(mask)
    log.info("Water cells: %s (%.2f%%)",
             f"{pool.water_cells:,}", pool.water_cells / mask.size * 100)
    db.save_mask(pool.mask)
    db.save_pool_state(pool, project_day_0=day_0)
    log.info("Pool initialised with day 0 = %s", day_0)
    log.info("Done. Next daily job will run against the fresh pool.")


if __name__ == "__main__":
    main()
