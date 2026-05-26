"""
Daily depletion step — orchestrates the pipeline.

Flow
----
1. Pull the last available day of GFW events.
2. Feed them into the OceanPool, chronologically.
3. Annotate each catch with GPS Position.
4. Persist: day stats, vessels, catches.
5. Rebuild and save the 3600×1800 depletion bitmap for the frontend.
6. Render the Catch-of-the-Day PDF.
7. Checkpoint the pool.
"""

from __future__ import annotations

import gc
import logging
import resource
import sys
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


def _rss_mb() -> int:
    # Current RSS — needs to drop after `del` to confirm the frees actually
    # work. Linux: /proc/self/status:VmRSS in kB. Reading the pseudo-file
    # is ~µs and we call this ~10x per daily job. macOS dev fallback:
    # resource.ru_maxrss (which is *peak* in bytes on Darwin, not current —
    # not great for diagnosis, but we deploy on Linux so it's fine).
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) // 1024
        except OSError:
            pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // (1024 * 1024)


DISPLAY_BITMAP_BYTES = DISPLAY_COLS * DISPLAY_ROWS * 2 // 8  # 1 620 000


def build_display_bitmap(pool: OceanPool) -> bytes:
    """
    Collapse the 36 000 × 18 000 backend stanza mask into a 3 600 × 1 800
    display bitmap. Each display tile aggregates a 10 × 10 block of stanza
    cells; **two bits per tile** are written to the wire, low bit first:

        bit 0 (low)  = all 100 sub-cells alive   (min over block)
        bit 1 (high) = any sub-cell still alive  (max over block)

    The four possible bit pairs map to three frontend states (the fourth
    is unreachable by construction):

        0b11 → INTACT     (all 100 alive)        — frontend "unangetastet"
        0b10 → PARTIAL    (some alive, some gone) — frontend "befischt"
        0b00 → DEPLETED   (all 100 erased)        — frontend "leer"
        0b01 → impossible (min=1 ⇒ max=1)

    Size on the wire: 3 600 × 1 800 × 2 / 8 = 1 620 000 bytes ≈ 1.55 MB.
    Gzip on the wire collapses the runs of identical tiles to a few
    hundred kB; FastAPI/Cloudflare apply that automatically.
    """
    mask2d = pool.mask.reshape(GRID_ROWS, GRID_COLS)
    blocks = mask2d.reshape(
        DISPLAY_ROWS, DISPLAY_FACTOR, DISPLAY_COLS, DISPLAY_FACTOR
    )
    any_alive = blocks.max(axis=(1, 3)).astype(np.uint8, copy=False)
    all_alive = blocks.min(axis=(1, 3)).astype(np.uint8, copy=False)
    # Interleave [tile0_min, tile0_max, tile1_min, tile1_max, …] so that
    # np.packbits(bitorder="little") puts (min, max) of tile N into bits
    # 2N and 2N+1 of the output stream — four tiles per byte.
    interleaved = np.stack((all_alive, any_alive), axis=-1).ravel()
    packed = np.packbits(interleaved, bitorder="little")
    return packed.tobytes()


def run_day(pool: OceanPool, events: list[dict],
            date: str, project_day_0: str,
            *, languages: tuple[str, ...] = ("en", "de")) -> dict:
    """Process one day of events. Mutates the pool in place.

    `languages` controls which PDF volumes are rendered inline. Default
    renders both EN and DE (legacy behaviour). The Railway daily job
    splits these across two subprocess calls — `("en",)` for the first
    pass (events + persist + EN) and a separate re-render path for DE
    (`pdf_builder.render_persisted_day`) — so the typst Rust heap from
    one language never coexists with the next.
    """
    log.info("run_day %s start: %d events, rss=%dMB", date, len(events), _rss_mb())
    # Chronological order. The ocean doesn't sort by anything else.
    events_sorted = sorted(events, key=lambda e: e.get("start", ""))

    per_vessel: dict[str, list[dict]] = defaultdict(list)
    vessels_meta: dict[str, dict] = {}
    all_catches: list[dict] = []

    # Defensive defaults: GFW occasionally serves an event without a
    # vessel name or a flag (and our DB columns are NOT NULL). Coerce
    # to safe placeholders right at the input boundary so the rest of
    # the pipeline never has to think about it.
    def _s(val, default="—"):
        s = (val or "").strip() if isinstance(val, str) else val
        return s if s else default

    for e in events_sorted:
        vname = _s(e.get("vessel_name"), "Unknown vessel")
        flag = _s(e.get("flag"), "—")
        vid_raw = e.get("vessel_id")
        catches = pool.process_event(e["lat"], e["lon"], e["fishing_hours"])
        vkey = vid_raw or f"{vname}::{flag}"
        vmeta = vessels_meta.setdefault(vkey, {
            "vessel_id": vkey,
            "vessel_name": vname,
            "flag": flag,
            "lat": e["lat"], "lon": e["lon"],
            "fishing_hours": 0.0,
            "stanzas": 0,
        })
        vmeta["fishing_hours"] += e["fishing_hours"]
        vmeta["lat"], vmeta["lon"] = e["lat"], e["lon"]  # last-known
        for c in catches:
            c["vessel_id"] = vkey
            c["vessel_name"] = vname
            c["flag"] = flag
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
        "fishing_hours": sum(e.get("fishing_hours", 0.0) for e in events_sorted),
        "depletion_percent": pool.depletion_percent,
        "depletion_factor": DEPLETION_FACTOR,
        "ocean_alive": pool.remaining,
    }
    log.info("events processed: %d catches across %d vessels, rss=%dMB",
             len(all_catches), len(per_vessel), _rss_mb())

    # ── Persist ──────────────────────────────────────────────────────
    # PDF rendering is the most fragile step: it pulls in WeasyPrint,
    # which in turn needs system-level Pango/HarfBuzz to shape text. If
    # any of that goes wrong on a host we don't fully control, we still
    # want the day's catches in the database — the PDF can be re-rendered
    # later from the persisted catches.
    # The canonical EN volume drives the `pdf_path` row written to the
    # `days` table; the DE volume is rendered alongside but tracked
    # only by filesystem presence (looked up via pdf_builder.latest_pdf
    # at request time). Either render is allowed to fail without
    # taking the day's persistence with it.
    pdf_path_str: str | None = None
    if "en" in languages:
        try:
            pdf_path = pdf_builder.render_daily_pdf(stats, per_vessel)
            pdf_path_str = str(pdf_path) if pdf_path else None
        except Exception as exc:  # noqa: BLE001
            log.exception("PDF render failed for %s, continuing without PDF: %s", date, exc)
    if "de" in languages:
        try:
            pdf_builder.render_daily_pdf(stats, per_vessel, language="de")
        except Exception as exc:  # noqa: BLE001
            log.exception("DE PDF render failed for %s, continuing: %s", date, exc)
    log.info("PDF render done (langs=%s), rss=%dMB", ",".join(languages), _rss_mb())

    db.record_day(stats, list(vessels_meta.values()), all_catches, pdf_path_str)

    # Free the per-day catch buffers before the bitmap/pool checkpoint —
    # all_catches alone can be 200-300 MB at 484k catches × ~600 B, and
    # per_vessel holds the same data partitioned. After db.record_day no
    # caller needs them; explicit del + gc.collect makes sure the bytes
    # are reclaimed before the next stage adds to the heap.
    all_catches.clear()
    del all_catches
    per_vessel.clear()
    del per_vessel
    vessels_meta.clear()
    del vessels_meta
    gc.collect()
    log.info("buffers freed, rss=%dMB", _rss_mb())

    # Prune older PDFs now that the new day's renders are on disk.
    # Freeing space here keeps the bitmap save (a ~648 MB tmp file +
    # rename) from tripping ENOSPC on the volume once the catches
    # table and historic PDFs have piled up.
    try:
        prune_stats = pdf_builder.prune_pdfs(is_final=pool.is_exhausted)
        log.info("prune_pdfs: archived=%d deleted=%d kept=%d freed=%.1fMB",
                 len(prune_stats["archived"]), len(prune_stats["deleted"]),
                 len(prune_stats["kept"]),
                 prune_stats["freed_bytes"] / (1024 * 1024))
    except Exception as exc:  # noqa: BLE001
        log.exception("prune_pdfs failed (continuing): %s", exc)

    bitmap = build_display_bitmap(pool)
    db.save_depletion_bitmap(bitmap)
    db.save_pool_state(pool, project_day_0)
    log.info("Day %s recorded: %d catches, %.6f%% depletion (pdf=%s, rss=%dMB)",
             date, stats["stanzas_caught"], stats["depletion_percent"],
             pdf_path_str or "none", _rss_mb())
    return stats


def run_latest(pool: OceanPool, project_day_0: str,
               fallback_json: Path | None = None,
               *, languages: tuple[str, ...] = ("en", "de")) -> dict:
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
    return run_day(pool, events, date=start, project_day_0=project_day_0,
                   languages=languages)
