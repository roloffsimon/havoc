"""
Build a (stats, poems) JSON fixture from the GFW events dump.

The fixture mirrors what `pdf_builder.render_daily_pdf` receives at
runtime. Used to iterate on Typst templates without booting the full
depletion pipeline.

Sizes:
  small  — first 5 vessels (~30 stanzas)        — fast template iteration
  medium — first 50 vessels (~300 stanzas)      — multi-page layout test
  full   — every event in the dump (~2k vessels) — stress test

Usage:
  python -m scripts.build_fixture --size small
  python -m scripts.build_fixture --size full --out fixtures/full_day.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

# Make package imports work whether run as module or script.
ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from app.grid import gps_to_grid, grid_to_latlon, GRID_COLS, GRID_ROWS
from app.stanza import generate_stanza_at
from app.entropy import stanza_entropy

DEPLETION_FACTOR = 3  # mirrors app.ocean_pool — avoids importing numpy in the fixture builder

EVENTS_PATH = ROOT.parent / "generation" / "events_2026-02-24.json"
DEFAULT_OUT = ROOT / "scripts" / "fixtures"


def _build_poems(events: list[dict]) -> dict[str, list[dict]]:
    """Group events by vessel; per event fan out into ceil(fishing_hours
    * DEPLETION_FACTOR) catches. First catch sits at the GPS cell
    ('source: gps'), the rest are drawn from neighbouring cells stepping
    along col/row to mimic the boustrophedon pool sweep ('source:
    pool'). Schema matches what `depletion.run_day` produces — that's
    what `pdf_builder.render_daily_pdf` consumes."""
    poems: dict[str, list[dict]] = defaultdict(list)
    cursor = 0
    for e in events:
        gps_col, gps_row = gps_to_grid(e["lat"], e["lon"])
        n = max(1, math.ceil(e.get("fishing_hours", 1.0) * DEPLETION_FACTOR))
        vkey = e.get("vessel_id") or f'{e.get("vessel_name", "Unknown")}::{e.get("flag", "??")}'
        vname = e.get("vessel_name") or "Unknown vessel"
        flag = e.get("flag") or "—"
        for k in range(n):
            if k == 0:
                col, row, source = gps_col, gps_row, "gps"
            else:
                cursor = (cursor + 7919) % (GRID_COLS * GRID_ROWS)
                col, row, source = cursor % GRID_COLS, cursor // GRID_COLS, "pool"
            stanza = generate_stanza_at(col, row)
            lat, lon = grid_to_latlon(col, row)
            poems[vkey].append({
                "vessel_id": vkey,
                "vessel_name": vname,
                "flag": flag,
                "lat": lat,
                "lon": lon,
                "stanza": stanza,
                "entropy": stanza_entropy(stanza),
                "source": source,
            })
    # Vessel-level sort: most catches first (matches HAVOC_PDF_TOP_N selection).
    # Per-vessel sort: high → low Shannon entropy (matches pdf_builder spec).
    for vkey in poems:
        poems[vkey].sort(key=lambda c: c["entropy"], reverse=True)
    return dict(sorted(poems.items(), key=lambda kv: -len(kv[1])))


def _build_stats(events: list[dict], poems: dict[str, list[dict]],
                 date: str = "2026-02-24") -> dict:
    return {
        "date": date,
        "events_processed": len(events),
        "vessels_active": len(poems),
        "stanzas_caught": sum(len(v) for v in poems.values()),
        "gps_catches": sum(len(v) for v in poems.values()),
        "pool_catches": 0,
        "fishing_hours": round(
            sum(e.get("fishing_hours", 0.0) for e in events), 2),
        "depletion_percent": 0.001234,
        "depletion_factor": 6,
        "ocean_alive": 460_000_000,
    }


def _select(events: Iterable[dict], size: str) -> list[dict]:
    events = list(events)
    if size == "full":
        return events
    # For small/medium we pick the N most active vessels — that's how the
    # production daily PDF cap works (HAVOC_PDF_TOP_N), and it's what
    # exercises the multi-stanza-per-vessel layout and column-break cases.
    n_vessels = {"small": 5, "medium": 50}[size]
    by_vessel: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        vkey = e.get("vessel_id") or f'{e.get("vessel_name", "??")}::{e.get("flag", "??")}'
        by_vessel[vkey].append(e)
    top_keys = sorted(by_vessel, key=lambda k: -len(by_vessel[k]))[:n_vessels]
    return [e for k in top_keys for e in by_vessel[k]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=("small", "medium", "full"), default="small")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--events", type=Path, default=EVENTS_PATH)
    args = ap.parse_args()

    events = json.loads(args.events.read_text())
    selected = _select(events, args.size)
    poems = _build_poems(selected)
    stats = _build_stats(selected, poems)

    out_path = args.out or (DEFAULT_OUT / f"sample_{args.size}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"stats": stats, "poems": poems},
                                   ensure_ascii=False, indent=2))
    print(f"Wrote {out_path} — {stats['vessels_active']} vessels, "
          f"{stats['stanzas_caught']} stanzas, "
          f"{out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
