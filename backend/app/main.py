"""
FastAPI service — the web-facing shell.

Endpoints
---------
GET /api/status            day counter, cells alive, depletion %, is_final
GET /api/vessels           last-known positions of active vessels
GET /api/depletion-grid    packed bitmap, 3600×1800 bits, display-aligned
GET /api/final-poem        only populated once the pool is exhausted
GET /api/catch-of-the-day  the day's PDF (or HTML fallback)

The frontend lives on Cloudflare Pages / GitHub Pages; this service
runs on Railway. CORS is wide-open for GET because nothing here is
private — everything is public data sampled from Global Fishing Watch
plus the project's own computed state.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from . import db, depletion, scheduler
from .ocean_pool import OceanPool

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)


# ── Runtime state: one OceanPool held in memory ──────────────────────
# 648 MB uint8 (GRID_ROWS × GRID_COLS). Kept in the process for the
# whole lifetime; checkpointed to disk after each daily run.

_pool: OceanPool | None = None
_project_day_0: str = os.environ.get("HAVOC_DAY_0", "2026-02-13")


def _get_pool() -> OceanPool:
    global _pool
    if _pool is None:
        raise RuntimeError("OceanPool not initialised — run scripts/init_pool.py first.")
    return _pool


def _load_pool() -> None:
    """
    Restore the pool from disk. The mask is rebuilt at init time by
    `scripts/init_pool.py`; here we only reopen it.
    """
    global _pool
    mask = db.load_mask()
    if mask is None:
        raise RuntimeError(
            f"No pool mask found at {db.MASK_PATH}. "
            "Run `python -m scripts.init_pool` first (see backend/README.md)."
        )
    state = db.load_pool_state() or {"cursor": 0, "direction": 1, "catch_count": 0}
    # NB: water_cells is derived from the mask, not from the state row —
    # the mask is authoritative.
    pool = OceanPool(mask, cursor=state["cursor"], direction=state["direction"])
    pool.catch_count = int(state.get("catch_count", 0))
    # water_cells is the *initial* count; we re-derive from mask + catches
    # so that the arithmetic (remaining = water_cells - catch_count) still
    # holds after restart.
    alive_now = int(pool.mask.sum())
    pool.water_cells = alive_now + pool.catch_count
    _pool = pool
    log.info("Pool loaded: %s alive / %s total (catches=%s)",
             f"{pool.remaining:,}", f"{pool.water_cells:,}", f"{pool.catch_count:,}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _load_pool()
    sched = AsyncIOScheduler(timezone="UTC")
    fallback = Path(os.environ.get("HAVOC_FALLBACK_JSON", "")) or None
    if fallback and not fallback.exists():
        fallback = None
    scheduler.attach(sched, scheduler.make_job(_get_pool, _project_day_0, fallback))
    sched.start()
    try:
        yield
    finally:
        sched.shutdown(wait=False)


app = FastAPI(title="Remorseless Havoc API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    pool = _get_pool()
    day0 = datetime.fromisoformat(_project_day_0).replace(tzinfo=timezone.utc)
    day_number = (datetime.now(timezone.utc).date() - day0.date()).days + 1
    return {
        "project_day_0": _project_day_0,
        "day": day_number,
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "cells_alive": pool.remaining,
        "water_cells_total": pool.water_cells,
        "depletion_percent": round(pool.depletion_percent, 6),
        "is_final": pool.is_exhausted,
    }


@app.get("/api/vessels")
def vessels():
    day = db.latest_day()
    if not day:
        return {"date": None, "vessels": []}
    return {"date": day["date"], "vessels": db.vessels_for(day["date"])}


@app.get("/api/depletion-grid")
def depletion_grid():
    """
    Packed bitmap, 3600×1800 = 810 000 bytes, LSB-first, row-major.
    1 bit = 'at least one backend cell in this display block is alive'.
    """
    path = db.depletion_bitmap_path()
    if not path.exists():
        # Synthesise one on the fly from the current pool so the very
        # first boot — before any daily run has happened — still serves
        # a consistent grid to the frontend.
        pool = _get_pool()
        bitmap = depletion.build_display_bitmap(pool)
        db.save_depletion_bitmap(bitmap)
    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/api/final-poem")
def final_poem():
    pool = _get_pool()
    poem = pool.final_poem()
    if poem is None:
        raise HTTPException(status_code=404, detail="Ocean not yet exhausted.")
    return poem


@app.get("/api/catch-of-the-day")
def catch_of_the_day():
    """
    Return the most recent daily volume (PDF, with HTML fallback).

    The website used to offer four size tiers and a downloadable archive
    of older days. Both were retired on 2026-04-25: the document is the
    document, and only today's is exposed publicly. Older days remain
    in the project's own weekly volumes (see pdf_builder.render_weekly_pdf),
    which live under data/pdfs/weekly/ and are not served from the API.
    """
    from . import pdf_builder
    path = pdf_builder.latest_pdf()
    if path is None:
        raise HTTPException(status_code=404, detail="No catch rendered yet.")
    media = "application/pdf" if path.suffix == ".pdf" else "text/html"
    return FileResponse(path, media_type=media, filename=path.name)


@app.get("/api/health")
def health():
    try:
        pool = _get_pool()
        return {"ok": True, "cells_alive": pool.remaining}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/debug/db")
def debug_db():
    """Diagnostic — what's actually persisted on the volume right now."""
    out: dict = {
        "db_path": str(db.DB_PATH),
        "db_exists": db.DB_PATH.exists(),
        "db_size_bytes": db.DB_PATH.stat().st_size if db.DB_PATH.exists() else None,
        "mask_path": str(db.MASK_PATH),
        "mask_exists": db.MASK_PATH.exists(),
        "mask_size_bytes": db.MASK_PATH.stat().st_size if db.MASK_PATH.exists() else None,
        "bitmap_path": str(db.DEPLETION_BITMAP_PATH),
        "bitmap_exists": db.DEPLETION_BITMAP_PATH.exists(),
    }
    try:
        with db.connect() as c:
            for table in ("days", "vessels_active", "catches", "pool_state"):
                try:
                    n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    out[f"{table}_count"] = n
                except Exception as e:  # noqa: BLE001
                    out[f"{table}_error"] = str(e)
            try:
                row = c.execute("SELECT * FROM pool_state WHERE id=1").fetchone()
                out["pool_state_row"] = dict(row) if row else None
            except Exception as e:  # noqa: BLE001
                out["pool_state_row_error"] = str(e)
            try:
                rows = c.execute(
                    "SELECT date, events, vessels, stanzas_caught, depletion_pct, pdf_path "
                    "FROM days ORDER BY date DESC LIMIT 5"
                ).fetchall()
                out["days_sample"] = [dict(r) for r in rows]
            except Exception as e:  # noqa: BLE001
                out["days_sample_error"] = str(e)
    except Exception as e:  # noqa: BLE001
        out["connect_error"] = str(e)
    return out
