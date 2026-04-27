"""
OceanPool — the single source of material truth.

============================================================================
  Conceptual anchor — computation has a material floor
============================================================================

The pool holds one bit per grid cell: alive or erased. That bitmap is the
entire state of the work. Every fishing event mutates it and is gone; what
remains is simply the shape of the survivors. There is no "stanza
database" — each cell's verse is recomputed from its lattice coordinates
whenever it is needed (`stanza.generate_stanza_at`). What the pool tracks
is only which cells still exist.

This is the project's counter-move to the combinatorial sublime.
Sea and Spar Between presents a lattice of 225 trillion stanzas — an
arithmetic that feels, in the browser, like an inexhaustible resource.
The pool reduces that feeling back to the physics of the ocean: finite,
enumerable, consumable. The seemingly unbounded computation is grounded
in a bit-array whose contents only ever go from True to False.

Two rules make this into a dramaturgy rather than a mere accounting:

    (1) GPS-first, then global pool. The first stanza of each fishing
        event is deleted at the ship's actual location. The remaining
        stanzas (DEPLETION_FACTOR per fishing hour) are drawn from a
        cursor that sweeps boustrophedon across the whole ocean. So a
        trawler in the North Sea can consume a verse in the Indian
        Ocean: industrial fishing is a planetary system, and local
        over-extraction has global consequences.

    (2) FINAL_FLOOR = 1. Exactly one water cell is held back from
        depletion. When the pool drops to one living cell, the
        depletion algorithm halts and the project comes to rest. That
        cell is the "final puff" — Moby-Dick, chapter CV, which also
        gives the work its title. It is the counterpart to the
        computational infinity of the source material: of 225 trillion
        possible stanzas, one is allowed to remain.

See `Konzepttext Website.md`, §5, for the dramaturgical framing.
============================================================================
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .grid import GRID_COLS, GRID_ROWS, gps_to_grid, grid_to_latlon
from .stanza import generate_stanza_at

# Conversion constant: 1 fishing hour = 3 stanzas.
#
# Rationale. GFW's Events API registers only discrete, high-confidence
# fishing events — it under-counts the total fishing effort visible in
# the parallel 4Wings Stats API (which aggregates every AIS position
# classified as fishing) by roughly a factor of 3.4. We round that
# empirical ratio to exactly 3 and take the communicable sentence as
# the rule of the work: one fishing hour deletes three stanzas. The
# precision loss (~3.5 → ~4 years projected runtime) is deliberate,
# in exchange for a factor that reads without a footnote.
# See generation/README.md §3 for the derivation and trade-off.
DEPLETION_FACTOR = 3.0


class OceanPool:
    """
    The live bitmap of surviving water cells.

    Invariants
    ----------
    * `mask[row * GRID_COLS + col] == True`  → cell is alive (stanza readable)
    * `mask[row * GRID_COLS + col] == False` → cell has been erased
    * `water_cells` is fixed at construction (set by the land mask).
    * `catch_count` is monotonically non-decreasing.
    * `remaining` never drops below `FINAL_FLOOR` (the final puff).
    """

    FINAL_FLOOR = 1

    def __init__(self, ocean_mask: np.ndarray,
                 cursor: int = 0,
                 direction: int = 1,
                 catch_count: int = 0):
        # The mask is a mutable flat uint8 array. Keeping it flat means
        # cell indexing is a single multiply-add and serialisation is
        # trivial (it's already a byte sequence). At 648 MB we want to
        # avoid gratuitous copies; only convert/copy when needed.
        if ocean_mask.dtype != np.uint8:
            ocean_mask = ocean_mask.astype(np.uint8)
        self.mask = ocean_mask.reshape(-1)
        self.water_cells = int(self.mask.sum())
        self.total = int(self.mask.size)
        self.catch_count = catch_count
        self.cursor = cursor
        self.direction = direction  # +1 = SW→NE sweep, -1 = NE→SW sweep

    # ── Accessors ────────────────────────────────────────────────────

    @property
    def remaining(self) -> int:
        return self.water_cells - self.catch_count

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= self.FINAL_FLOOR

    @property
    def depletion_percent(self) -> float:
        if self.water_cells == 0:
            return 0.0
        return self.catch_count / self.water_cells * 100

    def _idx_to_colrow(self, idx: int) -> tuple[int, int]:
        return idx % GRID_COLS, idx // GRID_COLS

    # ── Mutations ────────────────────────────────────────────────────

    def deplete(self, col: int, row: int) -> list[str]:
        """Flip one cell off and return its stanza."""
        self.mask[row * GRID_COLS + col] = 0
        self.catch_count += 1
        return generate_stanza_at(col, row)

    def next_from_pool(self) -> Optional[tuple[int, int, list[str]]]:
        """Draw the next living cell using the boustrophedon cursor."""
        if self.is_exhausted:
            return None

        while 0 <= self.cursor < self.total:
            idx = self.cursor
            self.cursor += self.direction
            if self.mask[idx]:
                col, row = self._idx_to_colrow(idx)
                return col, row, self.deplete(col, row)

        # End of sweep — flip direction and clamp the cursor.
        if not self.is_exhausted:
            self.direction *= -1
            self.cursor = max(0, min(self.total - 1, self.cursor))
            return self.next_from_pool()
        return None

    def process_event(self, lat: float, lon: float, fishing_hours: float) -> list[dict]:
        """
        Apply one fishing event. First stanza from the GPS cell (if
        still alive), remaining stanzas from the global pool.
        """
        catches: list[dict] = []
        if self.is_exhausted:
            return catches

        n_stanzas = max(1, int(fishing_hours * DEPLETION_FACTOR))
        target_col, target_row = gps_to_grid(lat, lon)

        for i in range(n_stanzas):
            if self.is_exhausted:
                break
            if i == 0 and self.mask[target_row * GRID_COLS + target_col]:
                stanza = self.deplete(target_col, target_row)
                catches.append({
                    "col": target_col, "row": target_row,
                    "lat": lat, "lon": lon,
                    "stanza": stanza, "source": "gps",
                })
            else:
                hit = self.next_from_pool()
                if hit is None:
                    break
                pcol, prow, stanza = hit
                plat, plon = grid_to_latlon(pcol, prow)
                catches.append({
                    "col": pcol, "row": prow,
                    "lat": plat, "lon": plon,
                    "stanza": stanza, "source": "pool",
                })
        return catches

    # ── Endgame ──────────────────────────────────────────────────────

    def final_poem(self) -> Optional[dict]:
        """
        The surviving cell as a three-stanza poem (12 lines).

        The one living cell keeps its deterministic Montfort/Strickland
        stanza; the two adjacent grid positions (east, south) supply
        the remaining stanzas. The poem is thus geographically anchored
        to a single square kilometre but reads as a triptych — the
        "final puff" of the project.
        """
        if not self.is_exhausted:
            return None
        alive = np.flatnonzero(self.mask)
        if len(alive) == 0:
            return None
        idx = int(alive[0])
        col, row = self._idx_to_colrow(idx)
        lat, lon = grid_to_latlon(col, row)
        east = (col + 1) % GRID_COLS
        south = min(row + 1, GRID_ROWS - 1)
        return {
            "col": col, "row": row, "lat": lat, "lon": lon,
            "poem": [
                generate_stanza_at(col, row),
                generate_stanza_at(east, row),
                generate_stanza_at(col, south),
            ],
        }
