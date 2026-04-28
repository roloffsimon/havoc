"""
Render a fixture day to PDF (Typst path).

Loads a JSON file produced by `build_fixture.py`, runs it through
`pdf_builder._build_daily_payload`, generates the cover via Pillow,
and writes the PDF to `scripts/out/`. Used to iterate on Typst
templates without standing up the full FastAPI service.

Usage:
  python -m scripts.render_test                 # small fixture
  python -m scripts.render_test --size full
  python -m scripts.render_test --size medium --out catch_test.pdf
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# pdf_builder imports app.db which mkdir's DATA_DIR. On a dev machine
# DATA_DIR isn't /data — let it default to backend/data via env override.
import os
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

from app import pdf_builder, typst_renderer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=("small", "medium", "full"), default="small")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    fixture = ROOT / "scripts" / "fixtures" / f"sample_{args.size}.json"
    data = json.loads(fixture.read_text())
    stats = data["stats"]
    poems = data["poems"]
    print(f"[fixture] {args.size}: {stats['vessels_active']} vessels, "
          f"{stats['stanzas_caught']} stanzas")

    out_dir = ROOT / "scripts" / "out"
    out_dir.mkdir(exist_ok=True)
    out_path = args.out or (out_dir / f"catch_{args.size}.pdf")

    # Mimic the production cover-path workflow.
    pdf_builder.TYPST_TMP_DIR.mkdir(parents=True, exist_ok=True)
    cover_path = pdf_builder.TYPST_TMP_DIR / f"cover_test_{args.size}.png"
    print(f"[cover] rendering Pillow PNG → {cover_path}")
    t0 = time.perf_counter()
    cover_path.write_bytes(pdf_builder._render_cover_image())
    print(f"[cover] {(time.perf_counter() - t0):.2f}s, "
          f"{cover_path.stat().st_size / 1024:.1f} KB")

    try:
        payload = pdf_builder._build_daily_payload(stats, poems, cover_path)
        print(f"[payload] {len(payload['poems'])} poems serialised")
        t0 = time.perf_counter()
        pdf_bytes = typst_renderer.render("daily", payload)
        elapsed = time.perf_counter() - t0
    finally:
        cover_path.unlink(missing_ok=True)

    out_path.write_bytes(pdf_bytes)
    print(f"[render] {elapsed:.2f}s wallclock, "
          f"{len(pdf_bytes) / 1024:.1f} KB → {out_path}")


if __name__ == "__main__":
    main()
