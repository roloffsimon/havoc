# Backend — *Remorseless Havoc*

FastAPI service. Runs the daily depletion step, keeps the OceanPool
state, renders the Catch-of-the-Day PDF, and exposes a small API the
frontend talks to.

## Topology

```
Cloudflare Pages / GitHub Pages        Railway
┌──────────────────────────────┐      ┌──────────────────────────────┐
│  website/index.html          │      │  backend/ (this directory)   │
│    canvas renderer           │─────▶│    FastAPI + APScheduler     │
│    Sea and Spar generator    │ HTTPS│    /api/status, /vessels,    │
│    loads /api/depletion-grid │      │    /depletion-grid, ...      │
│                              │      │                              │
│  website/public/             │      │    OceanPool (RAM)           │
│    land_mask_3600x1800.bin   │      │    SQLite (metadata)         │
└──────────────────────────────┘      │    mounted /data volume      │
                                      │                              │
                                      │   once a day:                │
                                      │     GFW Events API v3        │
                                      │     → depletion → PDF        │
                                      └──────────────────────────────┘
```

Everything the browser needs is static or public. The backend is the
only thing that holds authoritative state.

## Modules

| File | Role |
|---|---|
| `app/stanza.py` | Port of *Sea and Spar Between* (BSD, Montfort & Strickland 2010). The point at which the project takes over their code; annotated accordingly. |
| `app/grid.py` | 0.01° grid constants, GPS mapping, lattice mapping. The literal cash-out of the "fish at sea" metaphor. |
| `app/ocean_pool.py` | The state machine. Single-bit-per-cell mask, boustrophedon cursor, `FINAL_FLOOR = 1`. Annotated with the project's dramaturgy. |
| `app/gfw_client.py` | Events API v3 client with JSON fallback. |
| `app/entropy.py` | Shannon entropy — reading metric, applied at render time. |
| `app/depletion.py` | Daily pipeline: events → pool mutation → DB → display bitmap → PDF. |
| `app/pdf_builder.py` | HTML → PDF via WeasyPrint. |
| `app/db.py` | SQLite schema + mask/bitmap filesystem persistence. |
| `app/scheduler.py` | APScheduler cron (runs inside the API process). |
| `app/main.py` | FastAPI app, lifespan, routes. |
| `scripts/init_pool.py` | One-time bootstrap — builds/loads the mask and seeds the DB. |

## Local development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in GFW_TOKEN, leave the rest on defaults

# (A) Bootstrap the pool. Two ways:
python -m scripts.init_pool --from ../generation/ocean_mask.npz  # fast (~1s)
# -- or --
python -m scripts.init_pool                                      # live (10–30 min)

# (B) Run the API
uvicorn app.main:app --reload --port 8000

# (C) Trigger a day manually (optional — the scheduler will do this
#     automatically at 14:15 UTC):
python - <<'PY'
from pathlib import Path
from app.db import init_db, load_mask, load_pool_state
from app.ocean_pool import OceanPool
from app import depletion
init_db()
pool = OceanPool(load_mask())
state = load_pool_state() or {"cursor": 0, "direction": 1, "catch_count": 0}
pool.cursor, pool.direction, pool.catch_count = state["cursor"], state["direction"], state["catch_count"]
depletion.run_latest(pool, project_day_0="2026-02-13",
                     fallback_json=Path("../generation/events_2026-02-24.json"))
PY
```

Then from the frontend (`website/`), the browser should fetch
`http://localhost:8000/api/status` etc. Set `HAVOC_API_BASE` in
`website/index.html` to point at the backend for local testing.

## Endpoints

| Path | Returns |
|---|---|
| `GET /api/status` | Day counter, cells alive, depletion %, `is_final` flag. |
| `GET /api/vessels` | Most recent day's vessel list with coordinates. |
| `GET /api/depletion-grid` | Packed 3600×1800 bitmap (810 KB). One bit per display tile; each tile aggregates 100 stanza cells. `1 = tile alive` (INTACT or PARTIALLY DEPLETED), `0 = FULLY DEPLETED`. LSB-first, row-major. A future 2-bit format can split INTACT / PARTIAL / DEPLETED explicitly. |
| `GET /api/final-poem` | Only once `is_final`. The surviving cell + three-stanza poem. |
| `GET /api/catch-of-the-day` | The latest full PDF (or HTML fallback). Accepts `?size=full\|digest\|excerpt\|vessel`: `digest` = every 10th catch, `excerpt` = every 100th, `vessel` = the top vessel's day. Subsets are rendered lazily on first request and cached on disk. |
| `GET /api/health` | Liveness check — 503 if the pool isn't loaded. |

## Deploying on Railway

1. Push the repo root to GitHub.
2. Create a Railway project, point it at `backend/` (root directory).
3. Add a volume, mount it at `/data`.
4. Set environment variables (see `.env.example`). `DATA_DIR=/data`.
5. One-shot the init script from Railway's shell:
   `python -m scripts.init_pool --from ../generation/ocean_mask.npz`
   (copy `ocean_mask.npz` to the volume or bake it into the image).
6. Deploy. The daily scheduler runs inside the web process.

## Deploying the frontend separately

On Cloudflare Pages: set the build output to `website/`, no build
command. On GitHub Pages: push `website/` as a subtree to the `gh-pages`
branch, or use a Pages action that publishes `website/` directly.

Either way, edit `website/index.html` so `HAVOC_API_BASE` points at
your Railway URL (e.g. `https://havoc.up.railway.app`).
