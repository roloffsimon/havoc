#!/bin/sh
set -e

# Railway sometimes finishes mounting the /data volume a moment after
# the container starts. If we touch $DATA_DIR before then, writes land
# on the container's ~1 GB root filesystem and the 618 MB mask write
# blows it up — without ever producing a useful error.
mkdir -p "$DATA_DIR"
i=0
while [ "$(stat -c %d /)" = "$(stat -c %d "$DATA_DIR")" ] && [ "$i" -lt 60 ]; do
  echo "[start] Waiting for $DATA_DIR volume mount (${i}s)..."
  sleep 1
  i=$((i + 1))
done
if [ "$(stat -c %d /)" = "$(stat -c %d "$DATA_DIR")" ]; then
  echo "[start] WARNING: $DATA_DIR still on the container FS after 60s — proceeding anyway"
fi

if [ ! -f "$DATA_DIR/pool_mask.bin" ]; then
  echo "[start] No mask in $DATA_DIR — bootstrapping from ocean_mask.npz"
  python -m scripts.init_pool --from ocean_mask.npz
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
