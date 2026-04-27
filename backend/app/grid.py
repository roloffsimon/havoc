"""
Grid constants and coordinate conversions.

The grid is pinned to GFW's native 0.01° resolution, so one GFW data
cell, one geographic cell, and one stanza position coincide. This is
what lets a fishing event — detected from AIS signals — address a
stanza directly.
"""

# 360° / 0.01° = 36 000 columns ; 180° / 0.01° = 18 000 rows
# → 648 000 000 cells in total, ~460 000 000 remain after the land mask.
GRID_COLS = 36_000
GRID_ROWS = 18_000
GRID_TOTAL = GRID_COLS * GRID_ROWS
CELL_SIZE = 0.01
LAT_MIN = -90.0
LON_MIN = -180.0

# Display resolution used by the frontend canvas (one display cell = 10×10
# backend cells). The land mask bin shipped with the website is at this
# resolution; the depletion bitmap served by /api/depletion-grid must
# match exactly.
DISPLAY_COLS = 3600
DISPLAY_ROWS = 1800
DISPLAY_FACTOR = 10  # DISPLAY_COLS * DISPLAY_FACTOR == GRID_COLS

# The original Sea and Spar Between lattice (Montfort & Strickland, 2010):
# 14 992 384 × 14 992 384 = ~225 trillion positions on a toroidal plane.
# We map the 36 000 × 18 000 grid linearly into this lattice, so every
# water cell gets a unique, deterministic stanza.
LATTICE_SIZE = 14_992_384


def gps_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """GPS coordinates → (col, row). Mirrors GFW's cell_ll_lat/lon convention."""
    col = int((lon - LON_MIN) / CELL_SIZE)
    row = int((lat - LAT_MIN) / CELL_SIZE)
    col = max(0, min(GRID_COLS - 1, col))
    row = max(0, min(GRID_ROWS - 1, row))
    return col, row


def grid_to_latlon(col: int, row: int) -> tuple[float, float]:
    """Grid cell (col, row) → centre (lat, lon)."""
    lat = LAT_MIN + (row + 0.5) * CELL_SIZE
    lon = LON_MIN + (col + 0.5) * CELL_SIZE
    return lat, lon


def grid_to_lattice(col: int, row: int) -> tuple[int, int]:
    """
    Grid cell → (i, j) in the Sea and Spar Between lattice.

    Linear proportional mapping: the lattice is ~417× larger per axis
    than the grid, so each of the 648 million geographic cells lands on
    a distinct lattice position. Collisions are practically impossible.

    Conceptual anchor — this is the hinge of the whole project.
    Montfort & Strickland wrote that their work "contains as many
    verses as there are fish in the sea." *Remorseless Havoc*
    takes that metaphor literally: every square kilometre of real
    ocean is assigned one of those verses, and industrial fishing
    erases them the same way it erases fish.
    """
    i = int(col * (LATTICE_SIZE - 1) / (GRID_COLS - 1))
    j = int(row * (LATTICE_SIZE - 1) / (GRID_ROWS - 1))
    return i % LATTICE_SIZE, j % LATTICE_SIZE


def grid_to_display(col: int, row: int) -> tuple[int, int]:
    """Backend cell → display cell (10× coarser)."""
    return col // DISPLAY_FACTOR, row // DISPLAY_FACTOR
