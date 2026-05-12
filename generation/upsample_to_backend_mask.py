"""
upsample_to_backend_mask.py

Derives the backend pool mask (36 000 × 18 000, 0.01° cells) from the
already-generated frontend display mask (3 600 × 1 800, 0.1° cells).

Why this exists
---------------
The two masks used to be generated independently by `global-land-mask`
at their respective resolutions. At Sea-Ice/Antarctic-shelf boundaries
the two classifications diverged: a 0.1° display cell could land on
ocean while all 100 of its 0.01° sub-cells were classified as land.
Pool reported those tiles as fully depleted (all 100 sub-cells = 0),
the renderer drew them as black — a visual bug masquerading as
depletion.

By upsampling the display mask 10× along each axis, every display
ocean cell becomes 100 backend ocean sub-cells per construction.
Mask consistency is then guaranteed: `build_display_bitmap` can never
again report a `STATE_DEPLETED` tile in a region the frontend treats
as ocean.

Usage
-----
    python generation/upsample_to_backend_mask.py

Writes to `backend/ocean_mask.npz` (key `mask`).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "website" / "public" / "land_mask_3600x1800.bin"
DST = REPO / "backend" / "ocean_mask.npz"

DISPLAY_COLS, DISPLAY_ROWS = 3600, 1800
BACKEND_COLS, BACKEND_ROWS = 36_000, 18_000


def main() -> None:
    # Source is a flat byte stream, row-major, south->north (see
    # generate_display_mask.py). 1 = land, 0 = water.
    raw = np.fromfile(SRC, dtype=np.uint8)
    if raw.size != DISPLAY_COLS * DISPLAY_ROWS:
        raise RuntimeError(f"Expected {DISPLAY_COLS * DISPLAY_ROWS} bytes, got {raw.size}")
    display = raw.reshape(DISPLAY_ROWS, DISPLAY_COLS)

    # The pool's convention is the inverse: 1 = water (alive), 0 = land.
    water_display = (display == 0).astype(np.uint8)

    # Nearest-neighbour upsample: each display cell → 10 × 10 backend
    # sub-cells with the same value. `np.repeat` twice is the canonical
    # way and runs ~0.5 s for this size.
    backend = np.repeat(np.repeat(water_display, 10, axis=0), 10, axis=1)
    if backend.shape != (BACKEND_ROWS, BACKEND_COLS):
        raise RuntimeError(f"Upsample produced {backend.shape}, expected {(BACKEND_ROWS, BACKEND_COLS)}")

    water = int(backend.sum())
    total = backend.size
    print(f"Water cells: {water:,} ({water / total * 100:.2f}%)")
    print(f"Land cells:  {total - water:,}")

    DST.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DST, mask=backend)
    print(f"Wrote {DST.relative_to(REPO)}")


if __name__ == "__main__":
    main()
