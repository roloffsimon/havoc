#!/bin/sh
set -e

# Railway sometimes finishes mounting the /data volume a moment after
# the container starts. If we touch $DATA_DIR before then, writes land
# on the container's small root filesystem and either fill it up or
# disappear when the volume mounts over them.
#
# Using `mountpoint -q` rather than comparing stat device IDs: the
# overlay filesystem hands out different device IDs to newly created
# directories, so a stat-based check returns "mounted" immediately
# without ever waiting.
mkdir -p "$DATA_DIR"
i=0
while ! mountpoint -q "$DATA_DIR" && [ "$i" -lt 60 ]; do
  echo "[start] Waiting for $DATA_DIR volume mount (${i}s)..."
  sleep 1
  i=$((i + 1))
done
if ! mountpoint -q "$DATA_DIR"; then
  echo "[start] WARNING: $DATA_DIR not a mountpoint after 60s — proceeding anyway"
fi

if [ ! -f "$DATA_DIR/pool_mask.bin" ]; then
  echo "[start] No mask in $DATA_DIR — bootstrapping from ocean_mask.npz"
  python -m scripts.init_pool --from ocean_mask.npz
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
