"""
FastAPI service — the web-facing shell.

Endpoints
---------
GET /api/status            day counter, cells alive, depletion %, is_final
GET /api/vessels           last-known positions of active vessels
GET /api/depletion-grid    packed bitmap, 3600×1800 bits, display-aligned
GET /api/final-poem        only populated once the pool is exhausted
GET /api/catch-of-the-day  the day's PDF (or HTML fallback)
GET /api/catch-info        per-tier metadata for the download modal

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
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

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
    # The daily render runs in a subprocess (see scripts/run_daily.py and
    # the rationale in scheduler.py). After it succeeds the worker's
    # in-memory pool is stale, so we hand the scheduler our reload hook.
    scheduler.attach(sched, scheduler.make_job(_load_pool))
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

# JSON responses (notably /api/vessels at ~42 MB unkomprimiert) compress
# 8–12× — without this the frontend stalls for ~10 s before the live
# fleet replaces the mock vessels on first paint.
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Endpoints ────────────────────────────────────────────────────────

_PUBLIC_CACHE_5MIN = {"Cache-Control": "public, max-age=300"}


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
    # the bottom HUD's vessel/stanza counters need. Prefer the most
    # recent day that actually had events: GFW's publication lag has
    # been known to stretch from the documented ~72 h to 5–6 days, and
    # during those gaps the site would otherwise flip to 0 vessels /
    # 0 stanzas. The empty days still exist in the table for record-
    # keeping; they just don't drive the surface. `latest_day` is
    # absent on a fresh deploy where no day has been processed yet.
    latest = db.latest_active_day() or db.latest_day()
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
    return JSONResponse(content=out, headers=_PUBLIC_CACHE_5MIN)


@app.get("/api/vessels")
def vessels():
    # Same fallback as /api/status — keep the fleet card pinned to the
    # last day with real catches when GFW has been silent.
    day = db.latest_active_day() or db.latest_day()
    if not day:
        return JSONResponse(
            content={"date": None, "vessels": []},
            headers=_PUBLIC_CACHE_5MIN,
        )
    rows = db.vessels_for(day["date"])
    catches_by_id = db.catches_by_vessel(day["date"])
    # The renderer only checks `catches.length > 0` to decide whether to
    # paint a vessel, and the Fleet card only ever displays the first
    # stanza of the day — so one representative catch per vessel is all
    # the frontend actually consumes. `catch_count` carries the real
    # total for the "N stanzas" label. Without this trim the response is
    # ~42 MB for ~10k vessels with 444k inlined catches (visibly stalls
    # first paint by ~9 s on warm Railway).
    for v in rows:
        cs = catches_by_id.get(v["vessel_id"], [])
        v["catches"] = cs[:1]
        v["catch_count"] = len(cs)
    return JSONResponse(
        content={"date": day["date"], "vessels": rows},
        headers=_PUBLIC_CACHE_5MIN,
    )


@app.get("/api/depletion-grid")
def depletion_grid():
    """
    Packed bitmap, 3600×1800 tiles × 2 bits = 1 620 000 bytes, LSB-first,
    row-major. Two bits per tile encode the three frontend states
    (see depletion.build_display_bitmap for the bit layout).
    """
    path = db.depletion_bitmap_path()
    # Rebuild on first boot AND when a stale 1-bit bitmap (810 000 B)
    # from the pre-2-bit deploy is still on disk — first request after
    # rollout regenerates it.
    if not path.exists() or path.stat().st_size != depletion.DISPLAY_BITMAP_BYTES:
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
def catch_of_the_day(size: str = "selection", lang: str = "en"):
    """
    Return the most recent daily volume.

    Three tiers (`?size=...`):
      selection (default) — random ~1/10 of the day's fleet
      finecut             — random ~1/100
      onepiece            — one randomly chosen vessel

    Two languages (`?lang=...`):
      en (default) — original English volume
      de           — German edition (parallel `_de` artefact)

    Legacy aliases preserved for older website builds: `full` and
    `digest` map to selection; `excerpt` to finecut; `vessel` to
    onepiece. If the requested EN tier hasn't been rendered yet (e.g.
    a deploy before the tier code shipped), we fall back to whichever
    tier is on disk. Missing DE artefacts return 404 — no EN fallback,
    so the caller can detect the difference.
    """
    from . import pdf_builder
    aliases = {
        "selection": "selection", "full": "selection", "digest": "selection",
        "finecut": "finecut",     "excerpt": "finecut",
        "onepiece": "onepiece",   "vessel": "onepiece",
    }
    tier = aliases.get(size.lower().strip(), pdf_builder.DEFAULT_TIER)
    lang_aliases = {"en": "en", "english": "en", "de": "de", "deutsch": "de", "german": "de"}
    language = lang_aliases.get(lang.lower().strip(), "en")
    path = pdf_builder.latest_pdf(tier, language=language)
    if path is None:
        raise HTTPException(status_code=404, detail="No catch rendered yet.")
    media = "application/pdf" if path.suffix == ".pdf" else "text/html"
    return FileResponse(path, media_type=media, filename=path.name)


@app.get("/api/catch-info")
def catch_info(size: str = "selection", lang: str = "en"):
    """Metadata for the download confirmation modal.

    Returns the actual on-disk size, page count, and date for the
    chosen tier+language so the website can replace its mock figures.
    The page count is read from the PDF trailer via pypdf (xref-only,
    no full-content parse) — fast even for the largest tier.
    """
    from . import pdf_builder
    aliases = {
        "selection": "selection", "full": "selection", "digest": "selection",
        "finecut": "finecut",     "excerpt": "finecut",
        "onepiece": "onepiece",   "vessel": "onepiece",
    }
    tier = aliases.get(size.lower().strip(), pdf_builder.DEFAULT_TIER)
    lang_aliases = {"en": "en", "english": "en", "de": "de", "deutsch": "de", "german": "de"}
    language = lang_aliases.get(lang.lower().strip(), "en")
    path = pdf_builder.latest_pdf(tier, language=language)
    if path is None:
        raise HTTPException(status_code=404, detail="No catch rendered yet.")

    bytes_ = path.stat().st_size
    pages: int | None = None
    if path.suffix == ".pdf":
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(path)).pages)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("pypdf page count failed for %s: %r", path, exc)

    # Date — prefer the filename ("catch_<YYYY-MM-DD>_<tier>[_de].pdf")
    # since that's the date the volume was rendered for; fall back to
    # the most recent persisted day.
    date: str | None = None
    stem = path.stem
    if stem.startswith("catch_"):
        parts = stem.split("_")
        if len(parts) >= 2:
            date = parts[1]

    stanzas = None
    latest = db.latest_active_day() or db.latest_day()
    if latest:
        if not date:
            date = latest["date"]
        stanzas = latest["stanzas_caught"]

    return JSONResponse(
        content={
            "date": date,
            "tier": tier,
            "language": language,
            "filename": path.name,
            "bytes": bytes_,
            "pages": pages,
            "stanzas": stanzas,
        },
        headers=_PUBLIC_CACHE_5MIN,
    )


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


# Same background-task pattern as run-day, but for re-rendering a
# specific historic day from persisted catches. Used to rebuild PDFs
# wiped by an earlier emergency cleanup while the catch rows are still
# in the DB. Goes through scripts.run_daily as separate subprocess
# calls (EN, DE) so each typst.compile() run starts with a fresh Rust
# heap — same memory rationale as the scheduler (see scheduler.py).
_rerender_lock = __import__("threading").Lock()
_rerender_state: dict = {"running": False, "result": None,
                          "started_at": None, "finished_at": None,
                          "date": None}


def _rerender_day_worker(date: str):
    import subprocess
    import sys
    import traceback
    from datetime import datetime as _dt, timezone as _tz
    runs: list[dict] = []
    try:
        for lang in ("en", "de"):
            cmd = [sys.executable, "-m", "scripts.run_daily",
                   "--lang", lang, "--date", date]
            log.info("rerender subprocess: %s", " ".join(cmd))
            try:
                proc = subprocess.run(cmd, timeout=900, check=False)
                runs.append({"lang": lang, "rc": proc.returncode})
            except subprocess.TimeoutExpired:
                runs.append({"lang": lang, "rc": None, "timeout": True})
                break
            if proc.returncode != 0:
                # Don't proceed to DE if EN failed — the EN render
                # writes days.pdf_path, which the DE pass doesn't need
                # but the rest of the pipeline does.
                break
        # Worker's in-memory pool wasn't touched (rerender skips the
        # pool path) but reload defensively so we never serve a stale
        # pool after a debug action.
        try:
            _load_pool()
        except Exception as exc:  # noqa: BLE001
            log.warning("rerender: pool reload skipped (%s)", exc)
        ok = all(r.get("rc") == 0 for r in runs)
        with _rerender_lock:
            _rerender_state["result"] = {"ok": ok, "runs": runs}
    except Exception as exc:  # noqa: BLE001
        with _rerender_lock:
            _rerender_state["result"] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
                "runs": runs,
            }
    finally:
        with _rerender_lock:
            _rerender_state["running"] = False
            _rerender_state["finished_at"] = _dt.now(_tz.utc).isoformat()


@app.get("/api/debug/rerender-day")
def debug_rerender_day(request: Request):
    """Rebuild EN + DE PDFs for `?date=YYYY-MM-DD` from the DB's
    persisted catches. Spawns two subprocesses (one per language) the
    same way the scheduler does, so a heavy day (~600k+ catches) won't
    push the worker process past Railway's 8 GB ceiling.

    Returns immediately; poll /api/debug/rerender-day-status for the
    outcome (typst can run for a minute on heavy days)."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import threading
    from datetime import datetime as _dt, timezone as _tz
    date = request.query_params.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="provide ?date=YYYY-MM-DD")
    try:
        datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="bad date format (need YYYY-MM-DD)")
    with _rerender_lock:
        if _rerender_state["running"]:
            return {"started": False, "reason": "already running",
                    "started_at": _rerender_state["started_at"],
                    "date": _rerender_state["date"]}
        _rerender_state["running"] = True
        _rerender_state["result"] = None
        _rerender_state["started_at"] = _dt.now(_tz.utc).isoformat()
        _rerender_state["finished_at"] = None
        _rerender_state["date"] = date
    threading.Thread(target=_rerender_day_worker, args=(date,), daemon=True).start()
    return {"started": True,
            "started_at": _rerender_state["started_at"],
            "date": date,
            "poll": "/api/debug/rerender-day-status"}


@app.get("/api/debug/rerender-day-status")
def debug_rerender_day_status(request: Request):
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    with _rerender_lock:
        return dict(_rerender_state)


# ── Restore (regenerate) a day whose catch rows were lost ────────────
# Unlike rerender (which reads persisted catches to rebuild only PDFs),
# restore re-fetches the day from GFW and REBUILDS the catch rows against
# a throwaway scratch pool — for days that have days/vessels but zero
# catches (the journal_mode=MEMORY incident). The live pool is untouched.
_restore_lock = __import__("threading").Lock()
_restore_state: dict = {"running": False, "result": None,
                        "started_at": None, "finished_at": None,
                        "date": None}


def _restore_day_worker(date: str):
    import subprocess
    import sys
    import traceback
    from datetime import datetime as _dt, timezone as _tz
    runs: list[dict] = []
    try:
        # EN rebuilds the catches (--restore), then DE re-renders from the
        # rows EN just wrote (plain --date, same as the daily DE pass).
        passes = [["--lang", "en", "--restore", "--date", date],
                  ["--lang", "de", "--date", date]]
        for extra in passes:
            cmd = [sys.executable, "-m", "scripts.run_daily", *extra]
            log.info("restore subprocess: %s", " ".join(cmd))
            try:
                proc = subprocess.run(cmd, timeout=900, check=False)
                runs.append({"args": extra, "rc": proc.returncode})
            except subprocess.TimeoutExpired:
                runs.append({"args": extra, "rc": None, "timeout": True})
                break
            if proc.returncode != 0:
                # EN failed (no day row, empty day, or 0 catches from GFW) —
                # don't run DE against a day that wasn't rebuilt.
                break
        try:
            _load_pool()
        except Exception as exc:  # noqa: BLE001
            log.warning("restore: pool reload skipped (%s)", exc)
        ok = all(r.get("rc") == 0 for r in runs)
        with _restore_lock:
            _restore_state["result"] = {"ok": ok, "runs": runs}
    except Exception as exc:  # noqa: BLE001
        with _restore_lock:
            _restore_state["result"] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
                "runs": runs,
            }
    finally:
        with _restore_lock:
            _restore_state["running"] = False
            _restore_state["finished_at"] = _dt.now(_tz.utc).isoformat()


@app.get("/api/debug/restore-day")
def debug_restore_day(request: Request):
    """Rebuild the catch rows for `?date=YYYY-MM-DD` by re-fetching that
    day from GFW and replaying it against a throwaway scratch pool (the
    live depletion state is never touched). For days that kept their
    days/vessels rows but lost their catches. The regenerated catches are
    design-consistent but not byte-identical to the originals (pool draw
    order is non-seeded by design). Returns immediately; poll
    /api/debug/restore-day-status."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import threading
    from datetime import datetime as _dt, timezone as _tz
    date = request.query_params.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="provide ?date=YYYY-MM-DD")
    try:
        datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="bad date format (need YYYY-MM-DD)")
    with _restore_lock:
        if _restore_state["running"]:
            return {"started": False, "reason": "already running",
                    "started_at": _restore_state["started_at"],
                    "date": _restore_state["date"]}
        _restore_state["running"] = True
        _restore_state["result"] = None
        _restore_state["started_at"] = _dt.now(_tz.utc).isoformat()
        _restore_state["finished_at"] = None
        _restore_state["date"] = date
    threading.Thread(target=_restore_day_worker, args=(date,), daemon=True).start()
    return {"started": True,
            "started_at": _restore_state["started_at"],
            "date": date,
            "poll": "/api/debug/restore-day-status"}


@app.get("/api/debug/restore-day-status")
def debug_restore_day_status(request: Request):
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    with _restore_lock:
        return dict(_restore_state)


# ── Catch-table prune + one-time VACUUM ──────────────────────────────
_vacuum_lock = __import__("threading").Lock()
_vacuum_state: dict = {"running": False, "result": None,
                       "started_at": None, "finished_at": None}


def _vacuum_worker(keep_active_days: int):
    import traceback
    from datetime import datetime as _dt, timezone as _tz
    try:
        prune = db.prune_catches(keep_active_days=keep_active_days)
        log.info("vacuum worker: prune %s", prune)
        vac = db.vacuum()
        log.info("vacuum worker: vacuum %s", vac)
        with _vacuum_lock:
            _vacuum_state["result"] = {"ok": True, "prune": prune, "vacuum": vac}
    except Exception as exc:  # noqa: BLE001
        with _vacuum_lock:
            _vacuum_state["result"] = {
                "ok": False, "error": repr(exc),
                "traceback": traceback.format_exc()}
    finally:
        with _vacuum_lock:
            _vacuum_state["running"] = False
            _vacuum_state["finished_at"] = _dt.now(_tz.utc).isoformat()


@app.get("/api/debug/vacuum-db")
def debug_vacuum_db(request: Request):
    """Prune the catch log to the last `?keep=N` active days (default 3),
    then VACUUM to return the freed space to the filesystem. VACUUM
    refuses itself if free space is short (see db.vacuum), so an
    ENOSPC-prone volume can't be pushed over the edge. Runs in the
    background — poll /api/debug/vacuum-db-status."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import threading
    from datetime import datetime as _dt, timezone as _tz
    try:
        keep = int(request.query_params.get("keep", "3"))
    except ValueError:
        raise HTTPException(status_code=400, detail="keep must be an integer")
    if keep < 1:
        raise HTTPException(status_code=400, detail="keep must be >= 1")
    with _vacuum_lock:
        if _vacuum_state["running"]:
            return {"started": False, "reason": "already running",
                    "started_at": _vacuum_state["started_at"]}
        _vacuum_state["running"] = True
        _vacuum_state["result"] = None
        _vacuum_state["started_at"] = _dt.now(_tz.utc).isoformat()
        _vacuum_state["finished_at"] = None
    threading.Thread(target=_vacuum_worker, args=(keep,), daemon=True).start()
    return {"started": True, "keep_active_days": keep,
            "started_at": _vacuum_state["started_at"],
            "poll": "/api/debug/vacuum-db-status"}


@app.get("/api/debug/vacuum-db-status")
def debug_vacuum_db_status(request: Request):
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    with _vacuum_lock:
        return dict(_vacuum_state)


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
        out["disk"] = db.disk_usage()
    except Exception as e:  # noqa: BLE001
        out["disk_error"] = str(e)
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
            # Per-date catch-row count vs the days/vessels rows. A day
            # whose `events`/`vessels` are non-zero but `catch_rows` is 0
            # (or far below `stanzas_caught`) is one whose catches write
            # didn't survive — the signature of a record_day transaction
            # killed mid-INSERT under journal_mode=MEMORY.
            try:
                rows = c.execute(
                    """
                    SELECT d.date, d.events, d.vessels, d.stanzas_caught,
                           (SELECT COUNT(*) FROM catches x WHERE x.date = d.date)
                             AS catch_rows
                    FROM days d
                    ORDER BY d.date DESC
                    LIMIT 30
                    """
                ).fetchall()
                out["catch_integrity"] = [dict(r) for r in rows]
            except Exception as e:  # noqa: BLE001
                out["catch_integrity_error"] = str(e)
    except Exception as e:  # noqa: BLE001
        out["connect_error"] = str(e)
    return out


@app.get("/api/debug/gfw-probe")
def debug_gfw_probe(request: Request):
    """Direct probe of the Global Fishing Watch Events API. Pass
    `?start=YYYY-MM-DD&end=YYYY-MM-DD` (defaults to gfw_client's
    last_available_window). Returns the raw HTTP status, the API's
    reported `total`, the number of entries received in the first
    page, and a single sample entry. No depletion math — just the
    upstream answer, so we can tell whether 0-event days are GFW's
    truth or our problem."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import requests
    from . import gfw_client

    start = request.query_params.get("start")
    end = request.query_params.get("end")
    if not start or not end:
        start, end = gfw_client.last_available_window()

    try:
        token = gfw_client._token()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"token: {exc!r}"}

    params = {
        "datasets[0]": "public-global-fishing-events:latest",
        "start-date": start,
        "end-date": end,
        "limit": 5,
        "offset": 0,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{gfw_client.BASE_URL}/events",
                         headers=headers, params=params, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"request: {exc!r}",
                "url": f"{gfw_client.BASE_URL}/events", "params": params}

    out: dict = {
        "ok": r.ok,
        "status": r.status_code,
        "url": r.url.split("?")[0],
        "params": params,
    }
    body_text = r.text
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        data = None
    if isinstance(data, dict):
        entries = data.get("entries") or data.get("events") or []
        out["total"] = data.get("total")
        out["nextOffset"] = data.get("nextOffset")
        out["entries_returned"] = len(entries) if isinstance(entries, list) else None
        out["sample_entry_keys"] = sorted(entries[0].keys()) if entries else None
        out["sample_entry"] = entries[0] if entries else None
        out["other_top_level_keys"] = sorted(k for k in data.keys()
                                              if k not in {"entries", "events", "total", "nextOffset"})
    else:
        out["body_preview"] = body_text[:1000]
    return out


@app.get("/api/debug/pdfs-list")
def debug_pdfs_list(request: Request):
    """Diagnostic — list every Catch-of-the-Day PDF on the volume, grouped
    by location (PDF_DIR top level vs. archive subdirectory)."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    from . import pdf_builder
    return pdf_builder.list_pdfs()


@app.get("/api/debug/cleanup-pdfs")
def debug_cleanup_pdfs(request: Request):
    """Apply the archive/prune policy now: keep the latest render_date in
    PDF_DIR (so the API still serves), move the first + every-50th-day
    Selection PDFs into ARCHIVE_DIR, delete everything else.

    The daily pipeline runs this automatically after each new render;
    this endpoint exists for the initial backfill and for ad-hoc resets
    when the volume gets tight."""
    _debug_guard(request.headers.get("x-debug-token") or request.query_params.get("token"))
    import traceback
    from . import pdf_builder
    try:
        pool = _get_pool()
        is_final = bool(pool.is_exhausted)
    except Exception as exc:  # noqa: BLE001
        is_final = False
        log.warning("cleanup-pdfs: pool lookup failed (%s), assuming is_final=False", exc)
    try:
        return pdf_builder.prune_pdfs(is_final=is_final)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": repr(exc),
                "traceback": traceback.format_exc()}
