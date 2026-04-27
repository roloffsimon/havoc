"""
generate_display_mask.py

Generates the binary land mask for the frontend display.
Uses global-land-mask (GLOBE dataset, NOAA, ~1 km).

Resolution: 3600x1800 (0.1 deg per cell)
Output: public/land_mask_3600x1800.bin (flat binary, row-major, south->north)

Each display cell represents a 10x10 block of backend cells (0.01 deg).
"""

from global_land_mask import globe
import numpy as np

COLS, ROWS = 3600, 1800
CELL = 0.1

lon_centers = np.linspace(-180 + CELL/2, 180 - CELL/2, COLS)
mask = np.zeros((ROWS, COLS), dtype=np.uint8)

for row in range(ROWS):
    lat = -90 + (row + 0.5) * CELL
    is_land = globe.is_land(np.full(COLS, lat), lon_centers)
    mask[row, :] = is_land.astype(np.uint8)

with open("public/land_mask_3600x1800.bin", "wb") as f:
    f.write(mask.tobytes())

w = np.sum(mask == 0)
print(f"Water: {w:,} | Land: {ROWS*COLS - w:,} | {w/(ROWS*COLS)*100:.1f}% water")
