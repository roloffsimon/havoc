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

import ctypes
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path


def _preload_pdf_libs() -> None:
    """Force every shared object under /usr/lib/x86_64-linux-gnu into
    the process namespace so WeasyPrint's cffi dlopen calls find their
    transitive deps. Multiple passes — each pass picks up any lib whose
    deps a previous pass loaded. The directory isn't on the loader's
    default search path under Nixpacks, so we cannot rely on SONAME
    lookup at all; only already-loaded handles work.

    `RTLD_GLOBAL` puts the symbols in the global namespace; failures
    are silent (a few apt libs reference kernel-only deps we don't
    care about, and we'd just clutter the logs).
    """
    import glob
    import re
    candidates = sorted(
        p for p in glob.glob("/usr/lib/x86_64-linux-gnu/lib*.so.*")
        if re.search(r"\.so\.[0-9]+$", p)
    )
    loaded: set[str] = set()
    for _ in range(8):
        progress = False
        for path in candidates:
            if path in loaded:
                continue
            try:
                ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                loaded.add(path)
                progress = True
            except OSError:
                continue
        if not progress:
            break
    print(f"[preload] loaded {len(loaded)}/{len(candidates)} apt libs", flush=True)


# Run before any module that pulls in WeasyPrint (pdf_builder, depletion).
_preload_pdf_libs()

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from . import db, depletion, scheduler
from .ocean_pool import OceanPool

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# fontTools subsets every glyph and DEBUG-logs each step; on a 16k-vessel
# PDF that's tens of thousands of lines per render. Pin it to WARNING.
for noisy in ("fontTools", "fontTools.subset", "fontTools.ttLib"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
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
    out = {
        "project_day_0": _project_day_0,
        "day": day_number,
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "cells_alive": pool.remaining,
        "water_cells_total": pool.water_cells,
        "depletion_percent": round(pool.depletion_percent, 6),
        "is_final": pool.is_exhausted,
    }
    # Latest-day stats — what the website's "Catch of the Day" card and
    # the bottom HUD's vessel/stanza counters need. Comes from the
    # `days` row written by the most recent successful daily job;
    # absent on a fresh deploy where no day has been processed yet.
    latest = db.latest_day()
    if latest:
        # fishing_hours isn't stored on the days row directly — sum it
        # from the vessels_active rows for this date.
        from . import db as _db
        with _db.connect() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(fishing_hours), 0) AS fh FROM vessels_active WHERE date=?",
                (latest["date"],),
            ).fetchone()
            fh = float(row["fh"]) if row else 0.0
        out["latest_day"] = {
            "date": latest["date"],
            "stanzas_caught": latest["stanzas_caught"],
            "vessels": latest["vessels"],
            "events": latest["events"],
            "fishing_hours": round(fh, 2),
            "depletion_pct": latest["depletion_pct"],
        }
    return out


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


def _debug_guard(request_token: str | None) -> None:
    """Gate /api/debug/* behind a private env-var token.

    If HAVOC_DEBUG_TOKEN is unset, the endpoints look like they don't
    exist at all (404) — no information leak from probing. If the env
    var is set, callers must echo it back in the X-Debug-Token header
    (or `?token=` query string) to get through.
    """
    expected = os.environ.get("HAVOC_DEBUG_TOKEN", "").strip()
    if not expected or request_token != expected:
        raise HTTPException(status_code=404, detail="Not Found")


# Background-task state for /api/debug/run-day. The full daily run
# (28k events through pool, 16k-vessel PDF render) takes several
# minutes — far longer than Railway's HTTP timeout. We dispatch it
# to a worker thread and let the caller poll /api/debug/run-day-status.
_runday_lock = __import__("threading").Lock()
_runday_state: dict = {"running": False, "result": None, "started_at": None, "finished_at": None}


def _run_day_worker():
    import traceback
    from datetime import datetime as _dt, timezone as _tz
    pool = _get_pool()
    fallback = Path(os.environ.get("HAVOC_FALLBACK_JSON", "")) or None
    if fallback and not fallback.exists():
        fallback = None
    try:
        stats = depletion.run_latest(pool, _project_day_0, fallback_json=fallback)
        with _runday_lock:
            _runday_state["result"] = {"ok": True, "stats": stats}
    except Exception as exc:  # noqa: BLE001
        with _runday_lock:
            _runday_state["result"] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
                "pool_state_after_failure": {
                    "catch_count": pool.catch_count,
                    "cursor": pool.cursor,
                    "remaining": pool.remaining,
                },
            }
    finally:
        with _runday_lock:
            _runday_state["running"] = False
            _runday_state["finished_at"] = _dt.now(_tz.utc).isoformat()


@app.get("/api/debug/run-day")
def debug_run_day(request: Request):
    """Kick off the depletion job in a background thread; return immediately.

    Poll /api/debug/run-day-status to see the outcome. Synchronous in
    the request handler would block the uvicorn event loop long enough
    that Railway's healthcheck declares the container unhealthy and
    restarts it mid-render.
    """
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import threading
    from datetime import datetime as _dt, timezone as _tz
    with _runday_lock:
        if _runday_state["running"]:
            return {"started": False, "reason": "already running",
                    "started_at": _runday_state["started_at"]}
        _runday_state["running"] = True
        _runday_state["result"] = None
        _runday_state["started_at"] = _dt.now(_tz.utc).isoformat()
        _runday_state["finished_at"] = None
    threading.Thread(target=_run_day_worker, daemon=True).start()
    return {"started": True, "started_at": _runday_state["started_at"],
            "poll": "/api/debug/run-day-status"}


@app.get("/api/debug/run-day-status")
def debug_run_day_status(request: Request):
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    with _runday_lock:
        return dict(_runday_state)


@app.get("/api/debug/weasyprint")
def debug_weasyprint(request: Request):
    """Probe WeasyPrint import + a tiny render so we can see precisely
    why the daily job falls back to HTML. Returns the import error,
    a tiny PDF byte count if rendering works, and a list of the
    apt-installed libpango / libharfbuzz paths so we can confirm the
    runtime libs really arrived.
    """
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import glob
    import traceback
    import ctypes
    preload_results = {}
    for path in [
        "/usr/lib/x86_64-linux-gnu/libbz2.so.1.0",
        "/usr/lib/x86_64-linux-gnu/libmount.so.1",
        "/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0",
        "/usr/lib/x86_64-linux-gnu/libfreetype.so.6",
        "/usr/lib/x86_64-linux-gnu/libglib-2.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libgmodule-2.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libgobject-2.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libgio-2.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libharfbuzz.so.0",
        "/usr/lib/x86_64-linux-gnu/libfontconfig.so.1",
        "/usr/lib/x86_64-linux-gnu/libpango-1.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libpangoft2-1.0.so.0",
    ]:
        try:
            ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
            preload_results[path] = "ok"
        except Exception as e:  # noqa: BLE001
            preload_results[path] = repr(e)
    out: dict = {
        "libpango_glob":   glob.glob("/usr/lib/x86_64-linux-gnu/libpango*"),
        "libharfbuzz_glob": glob.glob("/usr/lib/x86_64-linux-gnu/libharfbuzz*"),
        "libfontconfig_glob": glob.glob("/usr/lib/x86_64-linux-gnu/libfontconfig*"),
        "libglib_glob":     glob.glob("/usr/lib/x86_64-linux-gnu/libglib*"),
        "libgobject_glob":  glob.glob("/usr/lib/x86_64-linux-gnu/libgobject*"),
        "libgio_glob":      glob.glob("/usr/lib/x86_64-linux-gnu/libgio*"),
        "libgmodule_glob":  glob.glob("/usr/lib/x86_64-linux-gnu/libgmodule*"),
        "libfreetype_glob": glob.glob("/usr/lib/x86_64-linux-gnu/libfreetype*"),
        "libbz2_anywhere":  glob.glob("/usr/lib/**/libbz2*", recursive=True) + glob.glob("/lib/**/libbz2*", recursive=True),
        "libmount_anywhere": glob.glob("/usr/lib/**/libmount*", recursive=True) + glob.glob("/lib/**/libmount*", recursive=True),
        "fonts_dejavu": glob.glob("/usr/share/fonts/truetype/dejavu/*.ttf"),
        "ld_library_path": os.environ.get("LD_LIBRARY_PATH", ""),
        "live_preload": preload_results,
    }
    try:
        from weasyprint import HTML  # type: ignore
        out["weasyprint_import"] = "ok"
        try:
            pdf_bytes = HTML(string="<h1>hello</h1>").write_pdf()
            out["weasyprint_render"] = f"ok ({len(pdf_bytes)} bytes)"
        except Exception as exc:  # noqa: BLE001
            out["weasyprint_render"] = repr(exc)
            out["weasyprint_render_traceback"] = traceback.format_exc()
    except Exception as exc:  # noqa: BLE001
        out["weasyprint_import"] = repr(exc)
        out["weasyprint_import_traceback"] = traceback.format_exc()
    return out


@app.get("/api/debug/db")
def debug_db(request: Request):
    """Diagnostic — what's actually persisted on the volume right now."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
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
