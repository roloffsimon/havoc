"""
One-time initialisation — build the ocean mask and the pool state.

Runs `global-land-mask` across the 18 000 × 36 000 grid, writes the
resulting bitmap to `$DATA_DIR/pool_mask.bin`, and persists a clean
pool_state row to SQLite. After this, the API process can boot and
restore the pool with `db.load_mask()` / `db.load_pool_state()`.

Usage
-----
    python -m scripts.init_pool                      # live run
    python -m scripts.init_pool --from generation/ocean_mask.npz
        reuse the mask already computed by the demo notebook (fast path)

This script is intentionally separate from the API process: the mask
computation takes 10–30 minutes at full resolution and has no place
in a web server's startup path.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

# Let this script run without a package-level sys.path tweak.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.grid import CELL_SIZE, GRID_COLS, GRID_ROWS, LAT_MIN, LON_MIN  # noqa: E402
from app.ocean_pool import OceanPool  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("init_pool")


def build_mask_live() -> np.ndarray:
    """Classify every cell via global-land-mask (GLOBE / NOAA, ~1 km)."""
    from global_land_mask import globe
    mask = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.uint8)
    lon_centres = np.linspace(
        LON_MIN + CELL_SIZE / 2,
        180.0 - CELL_SIZE / 2,
        GRID_COLS,
    )
    for row in range(GRID_ROWS):
        lat = LAT_MIN + (row + 0.5) * CELL_SIZE
        is_land = globe.is_land(np.full(GRID_COLS, lat), lon_centres)
        mask[row, :] = (~is_land).astype(np.uint8)
        if row % 1000 == 0:
            log.info("Rows %5d / %d", row, GRID_ROWS)
    return mask.ravel()


def load_from_npz(path: Path) -> np.ndarray:
    data = np.load(path)
    key = next(iter(data.files))
    arr = data[key]
    if arr.shape != (GRID_ROWS, GRID_COLS):
        raise ValueError(f"Expected {(GRID_ROWS, GRID_COLS)}, got {arr.shape}")
    return arr.astype(np.uint8).ravel()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", type=Path,
                    help="Reuse a pre-computed mask .npz (e.g. generation/ocean_mask.npz)")
    args = ap.parse_args()

    db.init_db()
    if args.src:
        log.info("Loading mask from %s", args.src)
        mask = load_from_npz(args.src)
    else:
        log.info("Building mask live (takes 10–30 minutes at full resolution) …")
        mask = build_mask_live()

    water = int(mask.sum())
    log.info("Water cells: %s (%.2f%%)", f"{water:,}", water / mask.size * 100)

    pool = OceanPool(mask)
    db.save_mask(pool.mask)
    db.save_pool_state(pool, project_day_0=str((__import__("datetime").date.today())))
    log.info("Pool initialised and persisted to %s", db.DATA_DIR)


if __name__ == "__main__":
    main()
