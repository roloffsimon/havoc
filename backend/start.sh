#!/bin/sh
set -e

# Railway mounts the /data volume shortly after the container starts.
# We must wait not only for the mount to appear in /proc/mounts
# (mountpoint -q) but also for the filesystem to be ready for I/O.
# Without the write test, SQLite fails with "disk I/O error".

# Phase 1: wait for the mount point to appear
i=0
while ! mountpoint -q "$DATA_DIR" 2>/dev/null && [ "$i" -lt 60 ]; do
  echo "[start] Waiting for $DATA_DIR volume mount (${i}s)..."
  sleep 1
  i=$((i + 1))
done
if ! mountpoint -q "$DATA_DIR" 2>/dev/null; then
  echo "[start] FATAL: $DATA_DIR not a mountpoint after 60s — aborting"
  exit 1
fi
echo "[start] $DATA_DIR is a mountpoint after ${i}s"

# Phase 2: wait for the volume to be writable (I/O ready)
j=0
while [ "$j" -lt 30 ]; do
  if touch "$DATA_DIR/.io_check" 2>/dev/null && rm -f "$DATA_DIR/.io_check" 2>/dev/null; then
    break
  fi
  echo "[start] Volume mounted but not yet writable (${j}s)..."
  sleep 1
  j=$((j + 1))
done
if [ "$j" -ge 30 ]; then
  echo "[start] FATAL: $DATA_DIR not writable after 30s — aborting"
  exit 1
fi
echo "[start] $DATA_DIR is writable after ${j}s"

if [ ! -f "$DATA_DIR/pool_mask.bin" ]; then
  echo "[start] No mask in $DATA_DIR — bootstrapping from ocean_mask.npz"
  # If a previous failed deploy left a half-written SQLite file on the
  # volume, subsequent opens can fail before init_pool gets a chance
  # to recreate it. Wipe any stale artefacts before we start fresh.
  rm -f "$DATA_DIR"/havoc.sqlite3 "$DATA_DIR"/havoc.sqlite3-journal "$DATA_DIR"/havoc.sqlite3-wal "$DATA_DIR"/havoc.sqlite3-shm
  python -m scripts.init_pool --from ocean_mask.npz
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
