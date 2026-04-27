"""
Persistence — SQLite for metadata and daily catch logs, filesystem for
the big binary blobs (mask, depletion bitmap).

Why split? The mask is 648 MB in memory (uint8, one byte per cell).
Shoving it through SQLite on every request would be wasteful; the
process keeps it in RAM and writes it to disk only at checkpoint time.
SQLite carries everything the API actually queries per request:
vessels, catches, day-level stats.

Environment
-----------
DATA_DIR (default "./data") — root for the sqlite file and the mask.
On Railway, point this at a mounted volume so state survives deploys.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .ocean_pool import OceanPool

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "havoc.sqlite3"
MASK_PATH = DATA_DIR / "pool_mask.bin"           # live OceanPool state (flat uint8)
DEPLETION_BITMAP_PATH = DATA_DIR / "depletion_3600x1800.bin"  # display-resolution bitmap

SCHEMA = """
CREATE TABLE IF NOT EXISTS pool_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    water_cells     INTEGER NOT NULL,
    catch_count     INTEGER NOT NULL,
    cursor          INTEGER NOT NULL,
    direction       INTEGER NOT NULL,
    updated_at      TEXT    NOT NULL,
    project_day_0   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS days (
    date            TEXT PRIMARY KEY,
    events          INTEGER NOT NULL,
    vessels         INTEGER NOT NULL,
    stanzas_caught  INTEGER NOT NULL,
    gps_catches     INTEGER NOT NULL,
    pool_catches    INTEGER NOT NULL,
    depletion_pct   REAL    NOT NULL,
    pdf_path        TEXT,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS vessels_active (
    date            TEXT    NOT NULL,
    vessel_id       TEXT    NOT NULL,
    vessel_name     TEXT    NOT NULL,
    flag            TEXT    NOT NULL,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    fishing_hours   REAL    NOT NULL,
    stanzas         INTEGER NOT NULL,
    PRIMARY KEY (date, vessel_id)
);

CREATE TABLE IF NOT EXISTS catches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    vessel_id       TEXT    NOT NULL,
    vessel_name     TEXT    NOT NULL,
    flag            TEXT    NOT NULL,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    col             INTEGER NOT NULL,
    row             INTEGER NOT NULL,
    source          TEXT    NOT NULL,  -- 'gps' | 'pool'
    entropy         REAL    NOT NULL,
    stanza_json     TEXT    NOT NULL   -- JSON list of 4 lines
);
CREATE INDEX IF NOT EXISTS idx_catches_date ON catches(date);
CREATE INDEX IF NOT EXISTS idx_catches_vessel ON catches(date, vessel_id);
"""


@contextmanager
def connect():
    # Railway's bind-mounted volume has limited support for the
    # filesystem operations SQLite normally relies on:
    #   - WAL needs an mmap of the -shm sidecar (returns EIO).
    #   - The default rollback journal needs to create a -journal
    #     file alongside the db, which also returns EIO here.
    #   - Repeated fcntl() locks behave inconsistently.
    # The pragmas below sidestep all three:
    #   journal_mode=MEMORY   keep the rollback journal in RAM only
    #   locking_mode=EXCLUSIVE  one fcntl lock at first write, then never
    #   synchronous=NORMAL    fewer fsyncs (still durable through writes)
    # Our writer is single-process and runs once a day, so this
    # configuration is appropriate.
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=MEMORY;")
    conn.execute("PRAGMA locking_mode=EXCLUSIVE;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
    log.info("DB initialised at %s", DB_PATH)


# ── OceanPool persistence ────────────────────────────────────────────

def save_mask(mask: np.ndarray) -> None:
    """Write the pool bitmap atomically (write-temp + rename)."""
    tmp = MASK_PATH.with_suffix(".bin.tmp")
    arr = mask if mask.dtype == np.uint8 else mask.astype(np.uint8, copy=False)
    arr.tofile(tmp)
    tmp.replace(MASK_PATH)


def load_mask() -> np.ndarray | None:
    if not MASK_PATH.exists():
        return None
    return np.fromfile(MASK_PATH, dtype=np.uint8)


def save_pool_state(pool: "OceanPool", project_day_0: str) -> None:
    """Persist cursor / catch count / direction and the mask itself."""
    save_mask(pool.mask)
    with connect() as c:
        c.execute(
            """
            INSERT INTO pool_state
              (id, water_cells, catch_count, cursor, direction, updated_at, project_day_0)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              water_cells = excluded.water_cells,
              catch_count = excluded.catch_count,
              cursor      = excluded.cursor,
              direction   = excluded.direction,
              updated_at  = excluded.updated_at
            """,
            (pool.water_cells, pool.catch_count, pool.cursor, pool.direction,
             datetime.now(timezone.utc).isoformat(), project_day_0),
        )


def load_pool_state() -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM pool_state WHERE id=1").fetchone()
    return dict(row) if row else None


# ── Depletion bitmap for the frontend ────────────────────────────────

def save_depletion_bitmap(packed: bytes) -> None:
    """Packed 3600×1800 bit array — served verbatim by /api/depletion-grid."""
    tmp = DEPLETION_BITMAP_PATH.with_suffix(".bin.tmp")
    tmp.write_bytes(packed)
    tmp.replace(DEPLETION_BITMAP_PATH)


def depletion_bitmap_path() -> Path:
    return DEPLETION_BITMAP_PATH


# ── Day / catch persistence ──────────────────────────────────────────

def record_day(stats: dict, vessels: list[dict], catches: list[dict],
               pdf_path: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("BEGIN IMMEDIATE;")
        try:
            c.execute(
                """
                INSERT OR REPLACE INTO days
                  (date, events, vessels, stanzas_caught, gps_catches, pool_catches,
                   depletion_pct, pdf_path, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (stats["date"], stats["events_processed"], stats["vessels_active"],
                 stats["stanzas_caught"], stats["gps_catches"], stats["pool_catches"],
                 stats["depletion_percent"], pdf_path, now),
            )

            c.execute("DELETE FROM vessels_active WHERE date=?", (stats["date"],))
            c.executemany(
                """INSERT INTO vessels_active
                   (date, vessel_id, vessel_name, flag, lat, lon, fishing_hours, stanzas)
                   VALUES (?,?,?,?,?,?,?,?)""",
                [(stats["date"], v["vessel_id"], v["vessel_name"], v["flag"],
                  v["lat"], v["lon"], v["fishing_hours"], v["stanzas"]) for v in vessels],
            )

            c.execute("DELETE FROM catches WHERE date=?", (stats["date"],))
            c.executemany(
                """INSERT INTO catches
                   (date, vessel_id, vessel_name, flag, lat, lon, col, row,
                    source, entropy, stanza_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [(stats["date"], c2["vessel_id"], c2["vessel_name"], c2["flag"],
                  c2["lat"], c2["lon"], c2["col"], c2["row"],
                  c2["source"], c2["entropy"], json.dumps(c2["stanza"]))
                 for c2 in catches],
            )
            c.execute("COMMIT;")
        except Exception:
            c.execute("ROLLBACK;")
            raise


def latest_day() -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM days ORDER BY date DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def vessels_for(date: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM vessels_active WHERE date=? ORDER BY fishing_hours DESC",
            (date,),
        ).fetchall()
    return [dict(r) for r in rows]


def catches_for(date: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM catches WHERE date=? ORDER BY vessel_id, id",
            (date,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["stanza"] = json.loads(d["stanza_json"])
        d.pop("stanza_json", None)
        out.append(d)
    return out
