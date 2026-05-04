"""
Catch-of-the-Day PDF — A4 poetry volume.

Layout
------
Page 1   — full-bleed cover, the "Grid-Glyph" design from
           archive/design_drafts/16_pdf_cover_b_grid_glyph.html: the page's
           Night-Graphite blue with a fine 2 mm grid running unbroken
           through both the ocean and the Instrument-Sans title.
Page 2+  — body, white paper, two-column stanzas. Each vessel becomes a
           poem in the volume: a right-aligned motto with the day's flag
           and stats, then the vessel name as the poem's heading, then
           the stanzas the ship erased that day, sorted high-to-low
           Shannon entropy.

Why split colour from B/W? File size. The cover carries the project's
visual identity in colour; the rest is type only, so the body pages
compress well and stay light when WeasyPrint flattens to PDF.

Sizing tiers were dropped on 2026-04-25: the website serves only the
day's full document.
"""

from __future__ import annotations

import gc
import logging
import os
import random
import re
import resource
import sys
from datetime import date as _date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

from . import db
from .db import DATA_DIR
from .ocean_pool import DEPLETION_FACTOR

log = logging.getLogger(__name__)


def _rss_mb() -> int:
    # Diagnostic for Railway OOM kills during the daily PDF job. ru_maxrss
    # is peak RSS since process start; Linux reports kB, macOS reports bytes.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss // 1024 if sys.platform.startswith("linux") else rss // (1024 * 1024)

# ── Render tiers ─────────────────────────────────────────────────────
# Daily volumes ship at three sizes:
#   selection — random ~1/10 of the day's fleet  (the canonical archive)
#   finecut   — random ~1/100 of the day's fleet (~150 vessels)
#   onepiece  — one randomly chosen vessel
# Random (not top-by-catch-count) so the document reads as a sample of
# the whole fleet rather than as the heaviest hitters. Sampling is
# deterministic per-date so reruns produce the same volume.
TIERS: tuple[str, ...] = ("selection", "finecut", "onepiece")
TIER_FRACTIONS: dict[str, int] = {
    "selection": 10,
    "finecut": 100,
    "onepiece": 0,   # always exactly 1
}
TIER_LABELS: dict[str, str] = {
    "selection": "Selection",
    "finecut":   "Fine Cut",
    "onepiece":  "One Piece",
}
DEFAULT_TIER = "selection"

# ── Language strings ─────────────────────────────────────────────────
# Translatable labels passed into the Typst payload. The DE volume
# substitutes these at render time and re-generates each catch's
# stanza from `(col, row)` via stanza_de.generate_stanza_at — the
# stored EN stanza is replaced. All other PDF prose (Introduction,
# colophon credits, etc.) stays English in this iteration; only the
# structural labels and the verse content are localised.
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "de")
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title":              "Catch of the Day",
        "section_opener":     "Catch of Day",
        "header_running":     "Catch of Day",
        "colophon_from":      "Catch of the Day from ",
    },
    "de": {
        "title":              "Tagesfang",
        "section_opener":     "Tagesfang",
        "header_running":     "Tagesfang",
        "colophon_from":      "Tagesfang vom ",
    },
}


def _normalise_language(language: str | None) -> str:
    lang = (language or DEFAULT_LANGUAGE).strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


PDF_DIR = DATA_DIR / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Typst-only scratch directory for the cover PNG. Sits inside the
# template tree so it's always inside the renderer's `root` and the
# image() call resolves without granting Typst access to the data
# volume. The directory is created lazily by the Typst path.
TYPST_TEMPLATE_DIR = Path(__file__).parent / "typst_templates"
TYPST_TMP_DIR = TYPST_TEMPLATE_DIR / ".tmp"

# Project day 0 — used to compute the daily Vol. number that prints on
# the cover.
_DAY_0 = os.environ.get("HAVOC_DAY_0", "2026-02-13")


# ── Vol. number helpers ──────────────────────────────────────────────

def _day_0_date() -> _date:
    return datetime.strptime(_DAY_0, "%Y-%m-%d").date()


def _vol_for(date_str: str) -> int:
    """Daily volume number — days since project day 0, 1-indexed."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d - _day_0_date()).days + 1


def _format_long_date(date_str: str) -> str:
    """`2026-04-10` → `10 April 2026`."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%-d %B %Y") if hasattr(d, "strftime") else date_str


# ── CSS ──────────────────────────────────────────────────────────────
# Typography mirrors the website's own PDF preview thumbnail (Ledger
# style, Newsreader italic) and the site's UI hierarchy: Instrument
# Sans for tracked uppercase headings, DM Mono for data/meta, and a
# single literary serif (Newsreader) for the verses themselves. The
# cover is the only colour page; body and colophon are pure black on
# white so WeasyPrint compresses them tightly.

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@500;700&family=DM+Mono:wght@400&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,300;1,6..72,400&display=swap');

@page {
  size: A4;
  /* One margin scheme for every body page. Side margins are wide so
     the header (top-left/top-right) and the body text share exactly
     the same horizontal extent — every section now reads against the
     same gutter, regardless of whether it's prose, a list, or two
     stanza columns. */
  margin: 32mm 28mm 22mm 28mm;
  @top-left {
    content: string(running-title) " " string(running-day);
    font-family: 'DM Mono', monospace;
    font-size: 7pt;
    letter-spacing: 0.18em;
    color: #888;
    margin-top: 12mm;
  }
  @top-right {
    content: string(running-date);
    font-family: 'DM Mono', monospace;
    font-size: 7pt;
    letter-spacing: 0.18em;
    color: #888;
    margin-top: 12mm;
  }
  @bottom-center {
    content: counter(page);
    font-family: 'DM Mono', monospace;
    font-size: 7pt;
    letter-spacing: 0.18em;
    color: #888;
  }
}
/* Running headers come from string()s set on the body wrapper. The
   half-title is page 1; the cover sits before pagination starts. */
.body {
  string-set:
    running-title attr(data-running-title),
    running-day attr(data-running-day),
    running-date attr(data-running-date);
}
@page cover {
  size: A4;
  margin: 0;
  background: #030a18;
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-right { content: none; }
}
@page titlepage {
  size: A4;
  margin: 22mm 28mm 16mm 28mm;
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-center { content: none; }
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body {
  font-family: 'Newsreader', 'Georgia', serif;
  font-size: 9.2pt;
  line-height: 1.32;
  color: #111;
  background: white;
}

/* ── COVER ──────────────────────────────────────────────────────── */
/* The cover lives in its own HTML document, rendered to a single-page
   PDF and prepended to the body PDF at write time. This is the only
   way to get the body's pagination to start at 1: WeasyPrint does
   not honour counter-reset/counter-set on the `page` counter from
   ordinary elements, so the cover-as-extra-page-of-the-same-PDF
   approach forced the half-title to be page 2. Splitting the cover
   into its own document sidesteps the counter entirely. */
.cover {
  page: cover;
  position: relative;
  width: 210mm; height: 297mm;
  background: #030a18;
  color: #d8dce2;
  overflow: hidden;
}
.cover .cover-img {
  position: absolute; top: 0; left: 0;
  width: 210mm; height: 297mm;
  display: block;
}
.cover-footer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 0 18mm 20mm 18mm;
  z-index: 5;
}
.cover-footer .rule {
  height: 0.3mm; background: rgba(216,220,226,0.28);
  margin-bottom: 6mm;
}
.cover-footer-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: baseline;
  column-gap: 10mm;
}
/* All three footer slots share the same DM Mono uppercase tracked
   register — title/author and day/date now read as one row. */
.cover-footer .vol,
.cover-footer .byline,
.cover-footer .date {
  font-family: 'DM Mono', monospace;
  font-style: normal; font-weight: 400;
  font-size: 8pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #d8dce2;
  white-space: nowrap;
}
.cover-footer .vol { text-align: left; }
.cover-footer .byline { text-align: center; }
.cover-footer .byline em { color: #d8dce2; font-style: normal; }
.cover-footer .date { text-align: right; }

/* ── BODY (white pages, B/W only) ──────────────────────────────── */

.poem {
  margin: 0 0 8mm 0;
  break-inside: auto;
}
.poem-head {
  break-after: avoid;
  margin-bottom: 4.5mm;
}
h2.vessel-name {
  display: inline;
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  font-size: 12.5pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #111;
  margin: 0;
}
.poem-head .vessel-flag {
  display: inline;
  font-family: 'DM Mono', monospace;
  font-weight: 400;
  font-size: 6.6pt;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #777;
  white-space: nowrap;
  margin-left: 1.4mm;
  vertical-align: 0.15em;
}

.stanzas {
  column-count: 3;
  column-gap: 6mm;
  column-fill: balance;
}
.stanza {
  break-inside: avoid;
  margin: 0 0 3mm 0;
}
.stanza .line {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-weight: 300;
  font-size: 8.5pt;
  line-height: 1.30;
  margin: 0;
  color: #1a1a1a;
  text-align: left;
}
.stanza .meta {
  font-family: 'DM Mono', monospace;
  font-size: 5.4pt;
  font-style: normal;
  color: #9a9a9a;
  margin-top: 0.5mm;
  letter-spacing: 0.06em;
  text-align: left;
}

/* ── PDF outline / bookmarks ──────────────────────────────────────
   WeasyPrint emits these as PDF outline entries. h1 inside .sr-only
   is invisible but still gets indexed, so the half-title and colophon
   show up in the PDF reader's outline pane. */
h1, h2.vessel-name {
  bookmark-level: none;
}
.toc h1, .about h1, .section-opener h1,
.index h1, .colophon h1 {
  bookmark-level: 1;
  bookmark-label: content();
  bookmark-state: open;
}
section.poem h2.vessel-name {
  bookmark-level: 2;
  bookmark-label: content();
  bookmark-state: closed;
}

.sr-only {
  position: absolute !important;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}

/* ── TABLE OF CONTENTS ─────────────────────────────────────────── */
/* page: titlepage suppresses the running header — the contents
   page is its own front-matter spread, no need for the title up top. */
.toc {
  page: titlepage;
  break-after: page;
}
.toc h1 {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  font-size: 11pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #111;
  margin: 0 0 8mm 0;
  padding-bottom: 1.4mm;
  border-bottom: 0.08mm solid rgba(0,0,0,0.55);
}
.toc ul {
  list-style: none;
  margin: 0; padding: 0;
}
.toc li {
  padding: 1.6mm 0;
  border-bottom: 0.05mm dotted rgba(0,0,0,0.18);
}
.toc li a {
  display: flex;
  align-items: baseline;
  gap: 4mm;
  text-decoration: none;
  color: #1a1a1a;
}
.toc .toc-name {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-weight: 300;
  font-size: 11pt;
  color: #1a1a1a;
  flex: 1;
}
.toc li a::after {
  content: target-counter(attr(href), page);
  font-family: 'DM Mono', monospace;
  font-size: 8pt;
  font-feature-settings: 'tnum';
  color: #555;
  letter-spacing: 0.06em;
}

/* ── SECTION OPENER (between About and the poems) ──────────────── */
/* Single big tracked-uppercase title, set in the same register as
   the per-vessel poem headings — this page sits as a typographic
   peer of the poems it introduces. */
.section-opener {
  page: titlepage;
  break-before: page;
  break-after: page;
  height: 247mm;
  display: flex;
  align-items: center;
  justify-content: center;
}
.so-title {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  font-size: 22pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #111;
  margin: 0;
  text-align: center;
  white-space: nowrap;
}

/* ── ABOUT (recto, after Contents) ─────────────────────────────── */
/* Spans the full content area defined by @page; no per-section
   max-width. Body text uses the same Newsreader italic register as
   the stanza lines, so prose and verse share a typographic family. */
.about {
  break-after: page;
}
.about h1 {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  font-size: 11pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #111;
  margin: 0 0 3.5mm 0;
  padding-bottom: 1.4mm;
  border-bottom: 0.08mm solid rgba(0,0,0,0.55);
}
.about p {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-weight: 300;
  font-size: 10pt;
  line-height: 1.55;
  color: #1a1a1a;
  margin: 0 0 4.2mm 0;
  text-align: justify;
  hyphens: auto;
}
.about em {
  /* the title is already italic; keep emphasis legible by going to
     normal-style, semibold weight */
  font-style: normal;
  font-weight: 500;
  color: #111;
}
.about a {
  color: inherit;
  text-decoration: none;
  border-bottom: 0.15mm solid rgba(0,0,0,0.30);
}
.about .mono {
  font-family: 'DM Mono', monospace;
  font-style: normal;
  font-size: 8.6pt;
  letter-spacing: 0.04em;
  color: #444;
}

/* ── INDEX of vessels ──────────────────────────────────────────── */
.index {
  break-before: page;
  break-after: page;
}
.index h1 {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 500;
  font-size: 11pt;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #111;
  margin: 0 0 3.5mm 0;
  padding-bottom: 1.4mm;
  border-bottom: 0.08mm solid rgba(0,0,0,0.55);
}
.index .ix-sub {
  font-family: 'DM Mono', monospace;
  font-size: 7pt;
  font-weight: 400;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #888;
  margin: 0 0 6mm 0;
}
.index ul {
  list-style: none;
  margin: 0; padding: 0;
  columns: 2;
  column-gap: 8mm;
  font-size: 9pt;
}
.index li {
  break-inside: avoid;
  padding: 0.6mm 0;
  border-bottom: 0.08mm dotted rgba(0,0,0,0.18);
}
.index li a {
  display: flex;
  align-items: baseline;
  gap: 1.2mm;
  text-decoration: none;
  color: #1a1a1a;
}
.index .ix-name {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-weight: 300;
  color: #1a1a1a;
  flex: 1;
}
.index .ix-meta {
  font-family: 'DM Mono', monospace;
  font-size: 6.4pt;
  letter-spacing: 0.10em;
  color: #888;
  text-transform: uppercase;
  white-space: nowrap;
}
/* WeasyPrint resolves target-counter(attr(href), page) to the page
   number that the named anchor lands on. */
.index li a::after {
  content: " · " target-counter(attr(href), page);
  font-family: 'DM Mono', monospace;
  font-size: 6.4pt;
  letter-spacing: 0.10em;
  color: #555;
  font-feature-settings: 'tnum';
  white-space: nowrap;
}

/* ── COLOPHON ─────────────────────────────────────────────────────
   Per spec: all info in the DM Mono register at one size, centred
   in the middle of the page; copyright sits separately at the foot.
   Plain block layout — explicit width + margin:auto for true
   horizontal centring (WeasyPrint's CSS Grid honours neither
   margin:auto nor justify-self reliably for the page counter use
   case we hit before, so we use the simplest mechanism here too). */
.colophon {
  page: titlepage;
  break-before: page;
  position: relative;
  height: 247mm;
  text-align: center;
}
.co-credits {
  position: absolute;
  left: 0; right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 130mm;
  margin: 0 auto;
  /* One font, one size, throughout this block. */
  font-family: 'DM Mono', monospace;
  font-weight: 400;
  font-size: 8.4pt;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  line-height: 1.7;
  color: #1a1a1a;
}
.co-credits p { margin: 0 0 5mm 0; }
.co-credits p:last-child { margin-bottom: 0; }
.co-credits .co-orn { margin: 2mm 0; }
.colophon .co-spacer-top { display: none; }
.co-credits em {
  font-style: normal;          /* preserve uppercase mono register */
  color: #111;
}
.co-credits a {
  color: inherit;
  text-decoration: none;
  border-bottom: 0.15mm solid rgba(0,0,0,0.40);
}
.co-credits .co-orn {
  letter-spacing: 0.4em;
  color: #888;
  padding-left: 0.4em;
}
.co-credits .co-author {
  font-weight: 400;
  /* visually distinct without leaving the mono register */
  border-bottom: 0.15mm solid rgba(0,0,0,0.40);
}
/* Copyright — pinned to the foot of the colophon section. */
.colophon .co-license {
  position: absolute;
  bottom: 0;
  left: 0; right: 0;
  width: 130mm;
  margin: 0 auto;
  font-family: 'DM Mono', monospace;
  font-size: 6.4pt;
  letter-spacing: 0.06em;
  text-transform: none;
  line-height: 1.55;
  color: #666;
}
.colophon .co-license em {
  font-style: normal;
  color: #333;
}

/* ── SCREEN-ONLY (browser preview only; WeasyPrint applies @page) ── */
@media screen {
  html, body { background: #1c1c20; }
  .cover {
    margin: 24px auto 0 auto;
    box-shadow: 0 16px 48px rgba(0,0,0,0.55);
  }
  main.body {
    display: block;
    width: 210mm;
    margin: 0 auto 24px auto;
    padding: 20mm 16mm 20mm 16mm;
    background: white;
    box-shadow: 0 16px 48px rgba(0,0,0,0.55);
  }
}
"""


# ── Cover SVG ────────────────────────────────────────────────────────
# Mirrors archive/design_drafts/16_pdf_cover_b_grid_glyph.html. The same
# fine 2 mm grid runs across the ocean and through the cream letters,
# inverted in colour inside the letter clip so the lattice stays
# unbroken. Kept here in code so the cover travels with the PDF
# pipeline rather than depending on a sibling HTML file.

PAGE_W, PAGE_H = 210, 297       # A4 mm
FC = 2.0                        # minor cell, mm
MAJOR = 20.0                    # major grid step, mm

OCEAN_DEEP = "#030a18"
CREAM      = "#d8dce2"


_FONT_DIR = Path(__file__).parent / "fonts"
_INSTRUMENT_BOLD = _FONT_DIR / "InstrumentSans-Bold.ttf"
_INSTRUMENT_MEDIUM = _FONT_DIR / "InstrumentSans-Medium.ttf"
_DM_MONO_MEDIUM = _FONT_DIR / "DMMono-Medium.ttf"
_NEWSREADER_DISPLAY_ITALIC = _FONT_DIR / "Newsreader-Italic-Display.ttf"
_BIG_SHOULDERS_BOLD = _FONT_DIR / "BigShouldersDisplay-Bold.ttf"

_COVER_DPI = 300                # → A4 cover ≈ 2480×3508 px, ~1 MB PNG
_COVER_PX_W = round(PAGE_W / 25.4 * _COVER_DPI)
_COVER_PX_H = round(PAGE_H / 25.4 * _COVER_DPI)


def _render_cover_image() -> bytes:
    """
    Rasterise the cover with Pillow.

    We do this graphically — and not as inline SVG — because WeasyPrint
    silently drops the contents of <clipPath>/<mask> when the clip is
    text-based, so the lattice could not be made to run unbroken
    through the title letters in pure SVG. Pillow renders text as an
    alpha mask which we composite ourselves, so the SAME 20 mm major
    grid passes through both the dark ocean and the cream letters.
    Returns PNG bytes.
    """
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    px_per_mm = _COVER_DPI / 25.4
    OCEAN = (3, 10, 24)
    CREAM = (216, 220, 226)

    # ── Outer layer: ocean blue + cream lattice ─────────────────────
    base = Image.new("RGB", (_COVER_PX_W, _COVER_PX_H), OCEAN)
    overlay = Image.new("RGBA", (_COVER_PX_W, _COVER_PX_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    minor_w = max(1, round(0.08 * px_per_mm))
    major_w = max(1, round(0.16 * px_per_mm))

    def paint_grid(draw, color: tuple[int, int, int],
                   minor_alpha: int, major_alpha: int):
        # Minor lines every 2 mm, skipping the 20 mm major positions.
        x = 0.0
        while x <= PAGE_W + 1e-6:
            if (x % MAJOR) > 1e-6:
                px = round(x * px_per_mm)
                draw.rectangle(
                    (px - minor_w // 2, 0,
                     px + minor_w - minor_w // 2 - 1, _COVER_PX_H),
                    fill=(*color, minor_alpha),
                )
            x += FC
        y = 0.0
        while y <= PAGE_H + 1e-6:
            if (y % MAJOR) > 1e-6:
                py = round(y * px_per_mm)
                draw.rectangle(
                    (0, py - minor_w // 2,
                     _COVER_PX_W, py + minor_w - minor_w // 2 - 1),
                    fill=(*color, minor_alpha),
                )
            y += FC
        # Major lines every 20 mm.
        x = 0.0
        while x <= PAGE_W + 1e-6:
            px = round(x * px_per_mm)
            draw.rectangle(
                (px - major_w // 2, 0,
                 px + major_w - major_w // 2 - 1, _COVER_PX_H),
                fill=(*color, major_alpha),
            )
            x += MAJOR
        y = 0.0
        while y <= PAGE_H + 1e-6:
            py = round(y * px_per_mm)
            draw.rectangle(
                (0, py - major_w // 2,
                 _COVER_PX_W, py + major_w - major_w // 2 - 1),
                fill=(*color, major_alpha),
            )
            y += MAJOR

    paint_grid(odraw, CREAM, minor_alpha=int(0.08 * 255),
               major_alpha=int(0.16 * 255))
    base = Image.alpha_composite(base.convert("RGBA"), overlay)

    # ── Letter region: cream fill crossed by the SAME major grid in
    #     ocean blue, drawn into a separate tile and pasted via the
    #     letter-shaped alpha mask. ──────────────────────────────────
    inner = Image.new("RGB", (_COVER_PX_W, _COVER_PX_H), CREAM)
    inner_overlay = Image.new("RGBA", (_COVER_PX_W, _COVER_PX_H), (0, 0, 0, 0))
    idraw = ImageDraw.Draw(inner_overlay)
    # Inside the letters we draw ONLY the major lines, otherwise the
    # 2 mm grid would look denser inside the letters than outside
    # (where it sits at 0.08 opacity and is barely visible). Slightly
    # thicker (0.20 mm) at higher opacity (0.85) so the lattice reads
    # clearly through the bold cream glyphs.
    inner_major_w = max(2, round(0.20 * px_per_mm))
    inner_alpha = int(0.85 * 255)
    x = 0.0
    while x <= PAGE_W + 1e-6:
        px = round(x * px_per_mm)
        idraw.rectangle(
            (px - inner_major_w // 2, 0,
             px + inner_major_w - inner_major_w // 2 - 1, _COVER_PX_H),
            fill=(*OCEAN, inner_alpha),
        )
        x += MAJOR
    y = 0.0
    while y <= PAGE_H + 1e-6:
        py = round(y * px_per_mm)
        idraw.rectangle(
            (0, py - inner_major_w // 2,
             _COVER_PX_W, py + inner_major_w - inner_major_w // 2 - 1),
            fill=(*OCEAN, inner_alpha),
        )
        y += MAJOR
    inner = Image.alpha_composite(inner.convert("RGBA"), inner_overlay)

    # ── Letter mask: Big Shoulders Display Bold. Tall, condensed,
    # sign-painter-monumental — feels closer to a logbook nameplate
    # than a generic grotesque, and the heavy strokes give the
    # ocean-blue lattice plenty of cream to bleed through.
    font_path = (_BIG_SHOULDERS_BOLD if _BIG_SHOULDERS_BOLD.exists()
                 else _INSTRUMENT_BOLD)
    if not font_path.exists():
        raise RuntimeError(f"Missing font: {font_path}")

    TRACKING_EM = 0.04       # subtle openness in the dense lockup
    target_w_mm = 178.0      # "CATCH OF" target width
    target_w_px = target_w_mm * px_per_mm

    def _tracked_width(font: "ImageFont.FreeTypeFont", text: str) -> float:
        """Sum of glyph advances + tracking gaps (no gap after last)."""
        font_em = font.size
        gap = font_em * TRACKING_EM
        widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
        return sum(widths) + gap * max(0, len(text) - 1)

    # Find font size that makes "CATCH OF" hit the target width.
    probe = ImageFont.truetype(str(font_path), 1000)
    natural_w = _tracked_width(probe, "CATCH OF")
    title_size = round(1000 * target_w_px / natural_w)
    font = ImageFont.truetype(str(font_path), title_size)

    def _draw_tracked(draw: "ImageDraw.ImageDraw", cx: float, cy: float,
                      text: str, font: "ImageFont.FreeTypeFont", fill: int):
        """Draw `text` centred on (cx, cy) with TRACKING_EM tracking."""
        gap = font.size * TRACKING_EM
        total = _tracked_width(font, text)
        x = cx - total / 2
        # ascent/descent from font metrics for vertical centring
        ascent, descent = font.getmetrics()
        y_baseline = cy + (ascent - descent) / 2
        for ch in text:
            bbox = font.getbbox(ch)
            ch_w = bbox[2] - bbox[0]
            # left-bearing offset from origin
            draw.text((x - bbox[0], y_baseline - ascent),
                      ch, font=font, fill=fill)
            x += ch_w + gap

    mask = Image.new("L", (_COVER_PX_W, _COVER_PX_H), 0)
    mdraw = ImageDraw.Draw(mask)
    cx = _COVER_PX_W / 2
    y1 = 105 * px_per_mm
    y2 = 167 * px_per_mm
    # Big Shoulders Display is built for caps-set sign-painting.
    _draw_tracked(mdraw, cx, y1, "CATCH OF", font, 255)
    _draw_tracked(mdraw, cx, y2, "THE DAY",  font, 255)

    # Composite the lattice-on-cream tile into the cover via the mask.
    cover = base.copy()
    cover.paste(inner, (0, 0), mask)

    out = BytesIO()
    cover.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _cover_data_uri() -> str:
    """Inline the cover PNG so the HTML stays a single self-contained
    artefact (the on-disk HTML in data/pdfs is useful for debugging)."""
    import base64
    return ("data:image/png;base64,"
            + base64.b64encode(_render_cover_image()).decode("ascii"))


def _render_cover_html(day_label: str, date_label: str) -> str:
    return f"""<div class="cover">
  <img class="cover-img" src="{_cover_data_uri()}" alt="">
  <div class="cover-footer">
    <div class="rule"></div>
    <div class="cover-footer-row">
      <span class="vol">Day {escape(day_label)}</span>
      <span class="byline">From <em>Remorseless Havoc</em> by Simon Roloff</span>
      <span class="date">{escape(date_label)}</span>
    </div>
  </div>
</div>"""


# ── Body rendering ───────────────────────────────────────────────────

def _stanza_html(c: dict) -> str:
    """One stanza block: 4 lines + the GPS coordinates beneath. All
    lines flush left (the per-line indent that mirrored the source
    text was dropped per spec); coordinates also left-aligned."""
    lines = "".join(
        f'<p class="line">{escape(line.strip())}</p>' for line in c["stanza"]
    )
    coords = f'{c["lat"]:.2f}°, {c["lon"]:.2f}°'
    return (
        '<div class="stanza">'
        + lines
        + f'<div class="meta">{coords}</div>'
        + '</div>'
    )


def _poem_html(vkey: str, raw_catches: list[dict]) -> str:
    """One vessel's poem: heading (with the flag set after the name in
    the small mono style) + 2-column stanzas. Per-vessel detail (GPS
    counts, centroid) is no longer printed alongside each poem — it
    lives in the colophon and the index instead."""
    if not raw_catches:
        return ""
    # Per-vessel arc: high → low Shannon entropy.
    catches = sorted(raw_catches, key=lambda c: c.get("entropy", 0), reverse=True)
    name = raw_catches[0]["vessel_name"] or vkey
    flag = raw_catches[0]["flag"] or "—"
    stanzas = "".join(_stanza_html(c) for c in catches)
    return (
        f'<section class="poem" id="vessel-{escape(vkey)}">'
        '<div class="poem-head">'
        f'<h2 class="vessel-name">{escape(name)}</h2>'
        f'<span class="vessel-flag">{escape(flag)}</span>'
        '</div>'
        f'<div class="stanzas">{stanzas}</div>'
        '</section>'
    )

# Note: the flag span sits as a sibling of <h2>, not a child, so the
# bookmark label (which is taken from the h2's text) doesn't include
# the flag code. Visually they're on the same baseline via
# `display: inline` on h2 and inline-block on the span.


def _colophon_html(stats: dict) -> str:
    """
    Last page. Five distinct blocks, each with its own typographic
    register so the page reads as a stack rather than a wall of text:

      1. Lead — 'Catch of the Day from {date}.'
      2. Stats — uniform DM Mono line covering Day, vessels, stanzas, depletion
      3. Project URL — remorselesshavoc.com on its own
      4. Credits — concept (link), then sources (two links)
      5. Set-in — the typefaces, in DM Mono
      6. Copyright — small, last
    """
    rendered = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    long_date = _format_long_date(stats["date"])
    day_n = _vol_for(stats["date"])
    return f"""
<section class="colophon" id="colophon">
  <h1 class="sr-only">Colophon</h1>
  <div class="co-spacer-top"></div>
  <div class="co-credits">
    <p>Catch of the Day from {escape(long_date)}.</p>

    <p>Day&nbsp;{day_n:03d} &middot; {stats['vessels_active']:,} vessels &middot;
      {stats['stanzas_caught']:,} stanzas &middot;
      +{stats['depletion_percent']:.6f}% depletion</p>

    <p><a href="http://remorselesshavoc.com">remorselesshavoc.com</a></p>

    <p>All code on GitHub:<br>
      <a href="https://github.com/roloffsimon/havoc">github.com/roloffsimon/havoc</a></p>

    <p class="co-orn">·   ·   ·</p>

    <p>Concept, implementation and webdesign:<br>
      <a href="https://roloffsimon.com" class="co-author">Simon Roloff</a>.</p>

    <p>With Stanza Generation from
      <a href="https://nickm.com/montfort_strickland/sea_and_spar_between/"><em>Sea
      and Spar Between</em></a> by Nick Montfort &amp;
      Stephanie&nbsp;Strickland,<br>
      and Fishing Data from
      <a href="https://globalfishingwatch.org/"><em>Global Fishing
      Watch</em></a>.</p>

    <p>Set in Big Shoulders Display, Newsreader,<br>
      Instrument Sans, and DM&nbsp;Mono.<br>
      Rendered {escape(rendered)}.</p>
  </div>
  <p class="co-license">
    &copy; Simon Roloff. The text of this document is released under
    the MIT License and may be reused, adapted and redistributed,
    provided that <em>Remorseless Havoc</em> (Simon Roloff, 2026) is
    credited as the source. The individual stanzas are derived from
    <em>Sea and Spar Between</em> (Montfort &amp; Strickland, 2010,
    BSD License).
  </p>
</section>"""


def _running_attrs(day_label: str, date_label: str) -> str:
    """The three data- attributes the @page running headers read via
    string()s. Header reads as 'Catch of Day 072 ... 25 APRIL 2026'
    — title and day number sit on the left, date on the right."""
    return (
        f'data-running-title="Catch of Day" '
        f'data-running-day="{escape(day_label)}" '
        f'data-running-date="{escape(date_label.upper())}"'
    )


def _section_opener_html(day_label: str) -> str:
    """
    Section title page introducing the poems. One line:
    'Catch of Day NNN' set in the poem-heading register (Instrument
    Sans 500 tracked uppercase). Sits between Introduction and the
    first vessel poem.
    """
    return f"""
<section class="section-opener" id="poems">
  <h1 class="so-title">Catch of Day&nbsp;{escape(day_label)}</h1>
</section>"""


def _toc_html(day_label: str) -> str:
    """
    Table of contents — sits between cover and Introduction. Lists
    the front-matter sections by name with target-counter() resolving
    to their start pages.
    """
    rows = [
        ("Introduction",                                "about"),
        (f"Catch of Day&nbsp;{escape(day_label)}",      "poems"),
        ("Index of vessels",                            "vessel-index"),
        ("Colophon",                                    "colophon"),
    ]
    items = "".join(
        f'<li><a href="#{anchor}">'
        f'<span class="toc-name">{name}</span>'
        f'</a></li>'
        for name, anchor in rows
    )
    return (
        '<section class="toc">'
        '<h1>Contents</h1>'
        f'<ul>{items}</ul>'
        '</section>'
    )


def _about_html(stats: dict) -> str:
    """
    The 'Introduction' page. Day-specific numbers come from `stats`;
    static framing text and titles/links are held here.

    Placeholders pulled from `stats`:
      date, fishing_hours, vessels_active, stanzas_caught,
      annual_depletion_pct, ocean_remaining_million (optional),
      runtime_years (optional).

    Links applied:
      Global Fishing Watch, Sea and Spar Between, Remorseless Havoc
      (project URL on first mention).
    """
    long_date = _format_long_date(stats["date"])
    ocean_remaining = stats.get("ocean_remaining_million", 460)
    runtime_years = stats.get("runtime_years", "four")
    annual_pct = stats.get("annual_depletion_pct", 28)
    return f"""
<section class="about" id="about">
  <h1>Introduction</h1>

  <p>On {escape(long_date)}, the industrial fishing fleet worldwide
  operated for {stats['fishing_hours']:,} hours with
  {stats['vessels_active']:,} vessels across the oceans. Their
  movements were recorded by satellite, interpreted as patterns of
  turns and drifts and catalogued by
  <a href="https://globalfishingwatch.org/"><em>Global Fishing
  Watch</em></a> as fishing events. On the website
  <a href="http://remorselesshavoc.com"><em>Remorseless Havoc</em></a>,
  each hour of that activity erased algorithmically generated
  language from a digital ocean. In a single day,
  {stats['stanzas_caught']:,} texts were lifted out of the sea and
  can no longer be read there. This document is the archive of that
  day's erasure.</p>

  <p>The texts are generated by an algorithm from
  <a href="https://nickm.com/montfort_strickland/sea_and_spar_between/"><em>Sea
  and Spar Between</em></a>, a work of digital literature developed by
  Nick Montfort and Stephanie Strickland in 2010: a grid of
  algorithmically generated stanzas, navigable in the browser,
  combinatorially assembled from language fragments by Emily Dickinson
  and Herman Melville. About 225 trillion stanzas extend in the
  browser almost endlessly in every direction, triggering the vertigo
  of combinatorics in an infinity with no practically reachable
  boundary from finite source material. Montfort and Strickland say
  their work contains as many verses as there are &ldquo;fish in the
  sea.&rdquo;</p>

  <p><em>Remorseless Havoc</em> takes that metaphor literally and maps
  the combinatory ocean onto the real seas of the world. It transfers
  Montfort and Strickland's stanzas into a grid spanning the whole
  globe with landmasses spared. Each cell represents a space of about
  one square kilometre, 1.1&nbsp;×&nbsp;1.1&nbsp;km at the equatorial
  meridian. This, obviously, leaves out the majority of stanzas from
  the originally generated trillions. Approximately
  {ocean_remaining}&nbsp;million verses remain distributed across the
  world's oceans. Subsequently, a second erasure follows, driven by
  the real fishing operations of real-world ships searching for actual
  fish in the sea.</p>

  <p>Their movement data is taken from the <em>Global Fishing
  Watch</em> Events API, which the website of the project calls once
  a day. GFW identifies fishing activity from AIS transponder signals
  — the automatic identification system that ships above a certain
  tonnage are required to carry — using a machine-learning classifier
  that distinguishes fishing behaviour from transit by reading
  characteristic turns, speed changes, and dwell patterns. The Events
  API reports only discrete, high-confidence fishing events. GFW's
  broader 4Wings dataset, which aggregates all AIS positions
  classified as fishing, reports approximately 3.4 times more
  activity. This is why the algorithm of <em>Remorseless Havoc</em>
  erases {DEPLETION_FACTOR} stanzas per fishing hour — a correction
  toward the actual scale of extraction from the seas.</p>

  <p>The first stanza of each vessel's poem is taken from the GPS
  coordinate of the fishing event — the geographic cell where the
  vessel operates, if it still contains language. When fishing
  continues at the same location, as it does in many cases,
  subsequent stanzas are drawn from a global pool in fixed order.
  Each vessel's catch is then ordered, to be published in this
  document, from high to low Shannon entropy, which is a measure of
  lexical diversity. The first stanzas are the linguistically richest
  with varied words and few repetitions. As the sequence progresses,
  the vocabulary narrows, more words recur, mirroring an arc from
  diversity to monotony and exhaustion.</p>

  <p>Depletion of the project's ocean is measured from the project's
  first day — each percentage point earned by real vessels, almost in
  real time (GFW takes 72 hours to analyze the satellite data, so
  what we can actually see are movements from three days before). At
  the current rate, approximately {annual_pct} percent of the ocean
  of language in <em>Remorseless Havoc</em> is emptied each year.
  Thus the project is estimated to run for roughly {runtime_years}
  years, until this sea is emptied. At that point, one last cell will
  remain, and its stanzas will form one last poem determined by the
  accumulated sequence of all deletions before it. The &ldquo;final
  puff&rdquo; if you will, that Melville foresaw when speculating
  about the ecological extinction of sea creatures in chapter CV of
  <em>Moby&nbsp;Dick</em>, &ldquo;Does the Whale's Magnitude
  Diminish?&nbsp;— Will He Perish?&rdquo;, from which the title of
  this project is taken.</p>
</section>"""


def _index_html(poems: dict[str, list[dict]]) -> str:
    """
    Index of vessels — alphabetic, with target-counter() resolving to
    the page on which each vessel's poem starts. WeasyPrint resolves
    the page numbers in a second layout pass, so the references just
    have to point at #vessel-{key} ids that the poem sections carry.
    """
    entries: list[tuple[str, str, str]] = []
    for key, catches in poems.items():
        if not catches:
            continue
        c0 = catches[0]
        name = c0["vessel_name"] or key
        flag = c0["flag"] or "—"
        entries.append((name, flag, key))
    entries.sort(key=lambda e: e[0].upper())
    items = []
    for name, flag, key in entries:
        anchor = f"vessel-{escape(key)}"
        items.append(
            f'<li><a href="#{anchor}">'
            f'<span class="ix-name">{escape(name)}</span>'
            f'<span class="ix-meta">{escape(flag.lower())}</span>'
            f'</a></li>'
        )
    return (
        '<section class="index" id="vessel-index">'
        '<h1>Index of vessels</h1>'
        f'<p class="ix-sub">{len(entries):,} entries · ordered alphabetically</p>'
        '<ul>' + "".join(items) + '</ul>'
        '</section>'
    )


def _render_cover_doc(stats: dict) -> str:
    """The cover as its own standalone HTML document — rendered to a
    single-page PDF and prepended to the body PDF at write time. See
    the .cover comment in CSS for why this isn't part of render_html."""
    day_n = _vol_for(stats["date"])
    day_label = f"{day_n:03d}"
    date_label = _format_long_date(stats["date"])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Catch of the Day — Cover — {escape(stats["date"])}</title>'
        f'<style>{CSS}</style></head><body>'
        + _render_cover_html(day_label, date_label)
        + '</body></html>'
    )


def _render_body_doc(stats: dict, poems: dict[str, list[dict]]) -> str:
    """The body (everything except the cover) as its own document.
    Page numbering naturally starts at 1 on the contents page.
    Order: Contents → About → Section opener → Poems → Index → Colophon.
    """
    day_n = _vol_for(stats["date"])
    day_label_short = f"{day_n:03d}"
    date_label = _format_long_date(stats["date"])
    toc = _toc_html(day_label_short)
    about = _about_html(stats)
    section_opener = _section_opener_html(day_label_short) if poems else ""
    body_parts = [_poem_html(k, v) for k, v in poems.items() if v]
    index = _index_html(poems) if poems else ""
    colophon = _colophon_html(stats)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Catch of the Day — {escape(stats["date"])}</title>'
        f'<style>{CSS}</style></head><body>'
        + f'<main class="body" {_running_attrs(day_label_short, date_label)}>'
        + toc
        + about
        + section_opener
        + "".join(body_parts)
        + index
        + colophon
        + '</main></body></html>'
    )


def render_html(stats: dict, poems: dict[str, list[dict]]) -> str:
    """
    Backwards-compatible single-document render. The cover and body
    sit in one HTML, separated by a page break. This loses the
    'half-title is page 1' invariant — for that, render the cover
    and body separately via _render_cover_doc / _render_body_doc and
    merge the resulting PDFs (see _merge_pdfs).
    """
    return _render_body_doc(stats, poems).replace(
        '<body>',
        '<body>' + _render_cover_html(
            f'{_vol_for(stats["date"]):03d}',
            _format_long_date(stats["date"])),
        1,
    )


# ── Disk / WeasyPrint ────────────────────────────────────────────────

def _artefact_name(date: str, ext: str) -> str:
    return f"catch_{date}.{ext}"


# ── Typst path ───────────────────────────────────────────────────────
# The daily-volume render goes through `app.typst_renderer.render`; the
# WeasyPrint path remains as a fallback selectable via HAVOC_PDF_ENGINE.
# Once Typst has run a week of production days without incident, the
# WeasyPrint code (and `_merge_pdfs`) is removed in the cleanup commit
# (see migration plan).

def _safe_label(s: str) -> str:
    """Sanitise a vessel-key for use as a Typst label. Typst labels
    must match `[A-Za-z0-9_-]+`; vessel-IDs from GFW occasionally
    contain colons, dots or slashes."""
    return "v_" + (re.sub(r"\W+", "_", s)[:60] or "unknown")


def _sample_for_tier(poems: dict[str, list[dict]], tier: str,
                      seed_str: str) -> dict[str, list[dict]]:
    """Deterministic random subsample of `poems` for the given tier.

    Sorting the keys before sampling is what makes the result stable:
    Python dicts preserve insertion order, but the source `poems` dict
    is built from event iteration order which is run-dependent. We sort
    by vkey, seed by date+tier, sample.
    """
    keys = sorted(poems.keys())
    n_total = len(keys)
    if n_total == 0:
        return {}
    if tier == "onepiece":
        target = 1
    else:
        denom = TIER_FRACTIONS.get(tier, 1)
        target = max(1, n_total // max(denom, 1)) if denom else 1
    if target >= n_total:
        return poems
    rng = random.Random(f"{seed_str}:{tier}")
    sampled = rng.sample(keys, target)
    return {k: poems[k] for k in sampled}


def _stanza_for_language(catch: dict, language: str) -> list[str]:
    """Return the 4-line stanza for a catch in the requested language.

    EN reuses the stored stanza (rendered when the catch happened).
    DE re-generates from `(col, row)` via stanza_de — the lattice
    position is deterministic so the result is stable across runs.
    """
    if language == "de":
        from . import stanza_de
        return stanza_de.generate_stanza_at(int(catch["col"]), int(catch["row"]))
    return list(catch["stanza"])


def _build_daily_payload(stats: dict, poems: dict[str, list[dict]],
                         cover_path: Path,
                         *, tier: str = DEFAULT_TIER,
                         fleet_total: int | None = None,
                         language: str = DEFAULT_LANGUAGE) -> dict:
    """Reshape the in-memory stats + poems into the JSON payload that
    `typst_templates/daily.typ` consumes via `sys.inputs.payload`.

    `poems` is the (possibly sampled) subset for this tier; `fleet_total`
    is the full fleet size before sampling, used by the Typst intro to
    explain the cut. If omitted, we fall back to len(poems).

    `cover_path` must sit inside `typst_templates/` so it can be
    addressed by a Typst-relative path; we compute the .typ-relative
    form and pass that, since absolute paths are interpreted relative
    to the Typst project root in a way that breaks on POSIX.

    Per-poem stanzas are pre-sorted by Shannon entropy desc; the
    poems themselves stay in their original (sampled) order — sorting
    by catch count would foreground heavy hitters and undo the
    intentionally-random sample.
    """
    cover_rel = cover_path.resolve().relative_to(TYPST_TEMPLATE_DIR.resolve())
    day_n = _vol_for(stats["date"])
    day_label = f"{day_n:03d}"
    long_date = _format_long_date(stats["date"])

    poems_list: list[dict] = []
    for vkey, catches in poems.items():
        if not catches:
            continue
        c0 = catches[0]
        sorted_catches = sorted(
            catches, key=lambda c: c.get("entropy", 0), reverse=True,
        )
        poems_list.append({
            "vkey": _safe_label(vkey),
            "name": c0.get("vessel_name") or vkey,
            "flag": c0.get("flag") or "—",
            "stanzas": [
                {
                    # Strip the per-line indent the stanza generator
                    # adds to lines 2 and 4 of each stanza — flush left
                    # is the documented spec (see pdf_builder._stanza_html
                    # in the WeasyPrint path).
                    "lines": [line.strip()
                              for line in _stanza_for_language(c, language)],
                    "lat": float(c["lat"]),
                    "lon": float(c["lon"]),
                    "entropy": float(c.get("entropy", 0.0)),
                    "source": c.get("source", "gps"),
                }
                for c in sorted_catches
            ],
        })
    # Stable, alphabetic order for the rendered selection — this echoes
    # the Index of vessels and reads as a calmer document than catch-
    # count-descending would.
    poems_list.sort(key=lambda p: p["name"].upper())

    selected_stanzas = sum(len(p["stanzas"]) for p in poems_list)
    fleet_total = fleet_total if fleet_total is not None else len(poems_list)

    rendered = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "stats": {
            "date": stats["date"],
            "day_label": day_label,
            "long_date": long_date,
            "vessels_active": int(stats["vessels_active"]),
            "stanzas_caught": int(stats["stanzas_caught"]),
            "fishing_hours": float(stats.get("fishing_hours", 0.0)),
            "depletion_percent": float(stats["depletion_percent"]),
            "depletion_factor": int(stats.get("depletion_factor", DEPLETION_FACTOR)),
            "ocean_remaining_million": stats.get("ocean_remaining_million", 460),
            "runtime_years": stats.get("runtime_years", "four"),
            "annual_depletion_pct": stats.get("annual_depletion_pct", 28),
            "rendered_utc": rendered,
            "vessels_active_str": f"{int(stats['vessels_active']):,}",
            "stanzas_caught_str": f"{int(stats['stanzas_caught']):,}",
            "fishing_hours_str": f"{float(stats.get('fishing_hours', 0.0)):,.0f}",
            "depletion_pct_str": f"{float(stats['depletion_percent']):.6f}",
            # Tier metadata read by the introduction to explain the cut.
            "tier": tier,
            "tier_label": TIER_LABELS.get(tier, tier.title()),
            "tier_fraction": TIER_FRACTIONS.get(tier, 1),
            "fleet_total_str": f"{fleet_total:,}",
            "selected_vessels": len(poems_list),
            "selected_vessels_str": f"{len(poems_list):,}",
            "selected_stanzas": selected_stanzas,
            "selected_stanzas_str": f"{selected_stanzas:,}",
            # Localised structural labels — read by the Typst template
            # for the running header, section opener, and document title.
            "language": language,
            "strings": STRINGS.get(language, STRINGS[DEFAULT_LANGUAGE]),
        },
        "poems": poems_list,
        "cover_path": str(cover_rel),
    }


def _lang_suffix(language: str) -> str:
    """File-name suffix for non-default languages.

    EN keeps the original `catch_{date}_{tier}.pdf` schema so existing
    bookmarks and CDN caches stay valid; DE adds `_de` before the
    extension (`catch_{date}_{tier}_de.pdf`).
    """
    return "" if language == DEFAULT_LANGUAGE else f"_{language}"


def _write_tier_artefact(stats: dict, poems: dict[str, list[dict]],
                          tier: str, *,
                          fleet_total: int,
                          cover_bytes: bytes,
                          out_dir: Path = PDF_DIR,
                          language: str = DEFAULT_LANGUAGE) -> Path:
    """Render a single tier (selection / finecut / onepiece) for the
    day. Cover PNG is passed in as bytes so all three tiers share one
    Pillow render (the cover is identical across tiers).
    """
    from . import typst_renderer

    date = stats["date"]
    TYPST_TMP_DIR.mkdir(parents=True, exist_ok=True)
    cover_path = TYPST_TMP_DIR / f"cover_{date}_{tier}{_lang_suffix(language)}.png"
    cover_path.write_bytes(cover_bytes)
    try:
        payload = _build_daily_payload(
            stats, poems, cover_path, tier=tier, fleet_total=fleet_total,
            language=language,
        )
        pdf_bytes = typst_renderer.render("daily", payload)
    finally:
        cover_path.unlink(missing_ok=True)

    pdf_path = out_dir / f"catch_{date}_{tier}{_lang_suffix(language)}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    pdf_size = len(pdf_bytes)
    sample_size = len(poems)
    log.info("PDF written to %s (%d bytes, typst, tier=%s, lang=%s, vessels=%d/%d, rss=%dMB)",
             pdf_path, pdf_size, tier, language, sample_size, fleet_total, _rss_mb())
    # Drop the per-tier buffers before returning. payload + json_str inside
    # typst.compile + pdf_bytes can each be 25-50 MB; the typst Rust heap
    # behind them isn't directly visible to Python's GC, so we at least
    # release everything we *can* see and let CPython reclaim the slabs.
    del payload, pdf_bytes
    return pdf_path


def _write_daily_artefacts_typst(stats: dict, poems: dict[str, list[dict]], *,
                                  out_dir: Path = PDF_DIR,
                                  stem: str | None = None,
                                  tiers: tuple[str, ...] = TIERS,
                                  language: str = DEFAULT_LANGUAGE) -> Path:
    """Render the day's volumes — one PDF per tier. Returns the path of
    the canonical (selection) PDF; the others sit alongside on disk and
    are addressable via `tier_pdf_path(date, tier)`. The Pillow cover is
    rendered once and reused.
    """
    fleet_total = len(poems)
    cover_bytes = _render_cover_image()
    paths: dict[str, Path] = {}
    for tier in tiers:
        # Sample with the same date+tier seed regardless of language so
        # the EN and DE volumes contain the same vessels, just rendered
        # in different verse.
        sub_poems = _sample_for_tier(poems, tier, stats["date"])
        paths[tier] = _write_tier_artefact(
            stats, sub_poems, tier,
            fleet_total=fleet_total,
            cover_bytes=cover_bytes,
            out_dir=out_dir,
            language=language,
        )
        # Force-collect between tiers: the typst Rust heap from the
        # previous compile may have left fragmented allocations; combined
        # with the next tier's sub_poems and payload they have pushed the
        # daily job past Railway's 8 GB ceiling on heavy days. del +
        # gc.collect gives CPython a chance to coalesce slabs before the
        # next tier inflates them again.
        del sub_poems
        gc.collect()
    return paths.get(DEFAULT_TIER) or next(iter(paths.values()))


def tier_pdf_path(date: str, tier: str = DEFAULT_TIER,
                   language: str = DEFAULT_LANGUAGE) -> Path:
    """Disk path for a tier-specific daily volume. Used by the API to
    serve `?size=...&lang=...`."""
    return PDF_DIR / f"catch_{date}_{tier}{_lang_suffix(language)}.pdf"


def _merge_pdfs(cover_pdf: bytes, body_pdf: bytes) -> bytes:
    """Concatenate cover + body and merge their outlines so the
    bookmark tree from the body document is preserved."""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter

    cover = PdfReader(BytesIO(cover_pdf))
    body = PdfReader(BytesIO(body_pdf))
    out = PdfWriter()
    for p in cover.pages:
        out.add_page(p)
    for p in body.pages:
        out.add_page(p)

    cover_offset = len(cover.pages)

    def _add_bookmarks(items, parent=None):
        last = parent
        for item in items:
            if isinstance(item, list):
                _add_bookmarks(item, last)
            else:
                page_idx = body.get_destination_page_number(item)
                last = out.add_outline_item(
                    item.title, page_idx + cover_offset, parent=parent,
                )

    _add_bookmarks(body.outline)
    buf = BytesIO()
    out.write(buf)
    return buf.getvalue()


def _write_daily_artefacts(stats: dict, poems: dict[str, list[dict]], *,
                            out_dir: Path = PDF_DIR,
                            stem: str | None = None) -> Path:
    """Daily volume: cover and body rendered separately and merged.
    The body PDF stands alone with page numbering starting at 1 — the
    cover sits outside the volume's pagination."""
    date = stats["date"]
    name_stem = stem or f"catch_{date}"

    body_html = _render_body_doc(stats, poems)
    cover_html = _render_cover_doc(stats)

    html_path = out_dir / f"{name_stem}.html"
    html_path.write_text(body_html, encoding="utf-8")

    try:
        from weasyprint import HTML  # type: ignore
    except Exception as exc:  # noqa: BLE001
        log.warning("WeasyPrint unavailable (%s) — HTML only at %s", exc, html_path)
        return html_path

    cover_pdf = HTML(string=cover_html).write_pdf()
    body_pdf = HTML(string=body_html).write_pdf()
    merged = _merge_pdfs(cover_pdf, body_pdf)

    pdf_path = out_dir / f"{name_stem}.pdf"
    pdf_path.write_bytes(merged)
    log.info("PDF written to %s", pdf_path)
    return pdf_path


def render_daily_pdf(stats: dict, poems: dict[str, list[dict]],
                     *, language: str = DEFAULT_LANGUAGE) -> Path | None:
    """Called by the daily pipeline to render the day's volumes.

    Renders three tiers of the day's catch (selection / fine cut /
    one piece) under the Typst engine and returns the path of the
    canonical Selection PDF. The whole day's fleet is sampled at
    different fractions per tier — see _sample_for_tier — so the cut
    reads as a sample of the fleet rather than as the heaviest hitters.

    `language`: "en" (default, original behaviour) or "de" — German
    edition. DE volumes re-generate each catch's stanza from its
    `(col, row)` via `stanza_de.generate_stanza_at` and write to a
    parallel `_de`-suffixed filename so EN and DE bookmarks stay
    independent.

    Knobs:
      HAVOC_PDF_SKIP=1     skip rendering entirely (record_day still
                           runs; the day's catches and vessels persist).
      HAVOC_PDF_ENGINE     "typst" (default behaviour) or "weasy" for
                           the legacy WeasyPrint pipeline. WeasyPrint
                           is tier-unaware — it renders a single PDF
                           covering the full fleet (or the legacy
                           HAVOC_PDF_TOP_N cap, if set). The WeasyPrint
                           path currently ignores `language` (EN only);
                           DE is Typst-only.
    """
    if os.environ.get("HAVOC_PDF_SKIP", "").strip() in {"1", "true", "yes"}:
        log.info("PDF: skipped (HAVOC_PDF_SKIP=1)")
        return None

    language = _normalise_language(language)
    engine = os.environ.get("HAVOC_PDF_ENGINE", "weasy").strip().lower()
    if engine == "typst":
        return _write_daily_artefacts_typst(stats, poems, language=language)

    if language != DEFAULT_LANGUAGE:
        log.warning("PDF: language=%s not supported on WeasyPrint engine; "
                    "skipping DE volume", language)
        return None

    # WeasyPrint legacy path — pre-tier behaviour with the env-var cap.
    top_n_raw = os.environ.get("HAVOC_PDF_TOP_N", "200").strip()
    if top_n_raw and top_n_raw != "0":
        top_n = int(top_n_raw)
        if len(poems) > top_n:
            ranked = sorted(poems.items(), key=lambda kv: -len(kv[1]))[:top_n]
            capped_poems = dict(ranked)
            log.info("PDF: capping volume to top %d vessels (of %d)", top_n, len(poems))
        else:
            capped_poems = poems
    else:
        capped_poems = poems
    return _write_daily_artefacts(stats, capped_poems)


# ── Public lookups (used by main.py) ─────────────────────────────────

def latest_pdf(tier: str | None = None,
               language: str | None = None) -> Path | None:
    """Newest daily artefact for the given tier (default: selection).

    EN files match `catch_*_{tier}.pdf`; DE files match
    `catch_*_{tier}_de.pdf`. Falls back to any `catch_*.pdf` if no
    tier-specific match exists, and finally to an HTML fallback if
    WeasyPrint left one behind on a prior deploy. The DE lookup is
    strict — there is no EN fallback for missing DE files (the caller
    sees a 404 and the user knows the DE volume isn't ready).
    """
    tier = tier or DEFAULT_TIER
    language = _normalise_language(language)
    suffix = _lang_suffix(language)
    tier_pdfs = sorted(PDF_DIR.glob(f"catch_*_{tier}{suffix}.pdf"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    if tier_pdfs:
        return tier_pdfs[0]
    if language != DEFAULT_LANGUAGE:
        # No EN-fallback for DE: missing DE artefact stays missing.
        return None
    pdfs = sorted(PDF_DIR.glob("catch_*.pdf"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if pdfs:
        # Filter out other-language artefacts so EN fallback doesn't
        # accidentally serve a `_de` file.
        pdfs = [p for p in pdfs if not p.stem.endswith("_de")]
    if pdfs:
        return pdfs[0]
    htmls = sorted(PDF_DIR.glob("catch_*.html"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    htmls = [p for p in htmls if not p.stem.endswith("_de")]
    return htmls[0] if htmls else None


def latest_date() -> str | None:
    p = latest_pdf()
    if not p:
        return None
    stem = p.stem
    return stem.replace("catch_", "", 1) if stem.startswith("catch_") else None


