#!/bin/sh
set -e

if [ ! -f "$DATA_DIR/pool_mask.bin" ]; then
  echo "[start] No mask in $DATA_DIR — bootstrapping from ocean_mask.npz"
  python -m scripts.init_pool --from ocean_mask.npz
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
