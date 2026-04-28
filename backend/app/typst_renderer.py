"""
Thin wrapper around `typst.compile`.

Locates templates under `app/typst_templates/` and the bundled font
files under `app/fonts/`, marshals a payload dict into a JSON string
that the templates read via `sys.inputs.payload`, and returns PDF
bytes.

Why this is its own module: keeps the Typst dependency confined to one
file (and out of `pdf_builder.py`'s import-time graph), so the
WeasyPrint path can still be exercised on machines that don't have
typst installed yet.
"""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "typst_templates"
FONT_DIR = Path(__file__).parent / "fonts"


def render(template: str, payload: dict) -> bytes:
    """Compile `app/typst_templates/{template}.typ` against `payload`
    and return the resulting PDF as bytes.

    `root` is set to the parent of TEMPLATE_DIR so the template can
    `#include` siblings via relative paths and so absolute image paths
    that fall under the project root resolve cleanly.
    """
    import typst  # imported lazily so machines without it can still import this module

    main = TEMPLATE_DIR / f"{template}.typ"
    return typst.compile(
        input=str(main),
        root=str(TEMPLATE_DIR.parent.parent),  # backend/ — covers app/ + scripts/
        font_paths=[str(FONT_DIR)],
        sys_inputs={"payload": json.dumps(payload, ensure_ascii=False)},
    )
