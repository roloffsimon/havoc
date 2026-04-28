"""
Daily depletion step — orchestrates the pipeline.

Flow
----
1. Pull the last available day of GFW events.
2. Feed them into the OceanPool, chronologically.
3. Annotate each catch with Shannon entropy (reading metric, measured
   at catch time but not used to re-order the catch log).
4. Persist: day stats, vessels, catches.
5. Rebuild and save the 3600×1800 depletion bitmap for the frontend.
6. Render the Catch-of-the-Day PDF.
7. Checkpoint the pool.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import db, gfw_client, pdf_builder
from .entropy import stanza_entropy
from .grid import (
    DISPLAY_COLS, DISPLAY_FACTOR, DISPLAY_ROWS, GRID_COLS, GRID_ROWS,
)
from .ocean_pool import DEPLETION_FACTOR, OceanPool

log = logging.getLogger(__name__)


def build_display_bitmap(pool: OceanPool) -> bytes:
    """
    Collapse the 36 000 × 18 000 backend stanza mask into a 3 600 × 1 800
    display bitmap. Each display tile aggregates a 10 × 10 block of stanza
    cells; one bit per tile is written to the wire:

        1 = tile is still *alive* (at least one stanza cell in the block
            has not yet been erased; the tile renders as INTACT or
            PARTIALLY DEPLETED in the frontend palette)
        0 = tile is *fully depleted* (all 100 stanza cells in the block
            have been erased; renders as the darkest tone)

    This single-bit encoding collapses INTACT and PARTIALLY DEPLETED into
    one value on the wire. A future 2-bit encoding can split them out so
    "partially depleted" becomes observable on the map directly; the
    frontend already has the third state reserved (STATE_PARTIAL in
    website/index.html).

    Size on the wire: 3 600 × 1 800 / 8 = 810 000 bytes ≈ 790 KB.
    """
    mask2d = pool.mask.reshape(GRID_ROWS, GRID_COLS)
    # "alive block" if any of the 100 sub-cells is still alive. Using a
    # reshape + max avoids a Python loop.
    blocks = mask2d.reshape(
        DISPLAY_ROWS, DISPLAY_FACTOR, DISPLAY_COLS, DISPLAY_FACTOR
    ).max(axis=(1, 3))
    alive = blocks.astype(np.uint8, copy=False).ravel()
    # Pack bits: 1 = alive, 0 = fully depleted.
    packed = np.packbits(alive, bitorder="little")
    return packed.tobytes()


def run_day(pool: OceanPool, events: list[dict],
            date: str, project_day_0: str) -> dict:
    """Process one day of events. Mutates the pool in place."""
    # Chronological order. The ocean doesn't sort by anything else.
    events_sorted = sorted(events, key=lambda e: e.get("start", ""))

    per_vessel: dict[str, list[dict]] = defaultdict(list)
    vessels_meta: dict[str, dict] = {}
    all_catches: list[dict] = []

    for e in events_sorted:
        catches = pool.process_event(e["lat"], e["lon"], e["fishing_hours"])
        vkey = e["vessel_id"] or f"{e['vessel_name']}::{e['flag']}"
        vmeta = vessels_meta.setdefault(vkey, {
            "vessel_id": vkey,
            "vessel_name": e["vessel_name"],
            "flag": e["flag"],
            "lat": e["lat"], "lon": e["lon"],
            "fishing_hours": 0.0,
            "stanzas": 0,
        })
        vmeta["fishing_hours"] += e["fishing_hours"]
        vmeta["lat"], vmeta["lon"] = e["lat"], e["lon"]  # last-known
        for c in catches:
            c["vessel_id"] = vkey
            c["vessel_name"] = e["vessel_name"]
            c["flag"] = e["flag"]
            c["entropy"] = stanza_entropy(c["stanza"])
            per_vessel[vkey].append(c)
            all_catches.append(c)
        vmeta["stanzas"] += len(catches)

    stats = {
        "date": date,
        "events_processed": len(events_sorted),
        "vessels_active": len(per_vessel),
        "stanzas_caught": len(all_catches),
        "gps_catches": sum(1 for c in all_catches if c["source"] == "gps"),
        "pool_catches": sum(1 for c in all_catches if c["source"] == "pool"),
        "depletion_percent": pool.depletion_percent,
        "depletion_factor": DEPLETION_FACTOR,
        "ocean_alive": pool.remaining,
    }

    # ── Persist ──────────────────────────────────────────────────────
    # PDF rendering is the most fragile step: it pulls in WeasyPrint,
    # which in turn needs system-level Pango/HarfBuzz to shape text. If
    # any of that goes wrong on a host we don't fully control, we still
    # want the day's catches in the database — the PDF can be re-rendered
    # later from the persisted catches.
    try:
        pdf_path = pdf_builder.render_daily_pdf(stats, per_vessel)
        pdf_path_str = str(pdf_path) if pdf_path else None
    except Exception as exc:  # noqa: BLE001
        log.exception("PDF render failed for %s, continuing without PDF: %s", date, exc)
        pdf_path_str = None

    db.record_day(stats, list(vessels_meta.values()), all_catches, pdf_path_str)

    bitmap = build_display_bitmap(pool)
    db.save_depletion_bitmap(bitmap)
    db.save_pool_state(pool, project_day_0)
    log.info("Day %s recorded: %d catches, %.6f%% depletion (pdf=%s)",
             date, stats["stanzas_caught"], stats["depletion_percent"],
             pdf_path_str or "none")
    return stats


def run_latest(pool: OceanPool, project_day_0: str,
               fallback_json: Path | None = None) -> dict:
    """Fetch the last-available day from GFW (or fallback) and run it."""
    start, end = gfw_client.last_available_window()
    try:
        events = gfw_client.fetch_events(start, end)
    except Exception as exc:
        log.warning("GFW fetch failed: %s", exc)
        if not fallback_json or not fallback_json.exists():
            raise
        log.info("Falling back to %s", fallback_json)
        events = gfw_client.load_events_from_file(str(fallback_json))
    return run_day(pool, events, date=start, project_day_0=project_day_0)
