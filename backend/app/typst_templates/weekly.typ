// weekly.typ — one-week archive volume.
//
// Bundles 7 daily sections back-to-back. Reuses the daily layout's
// per-vessel poem rendering and the cover-overlay pattern; the week's
// cover footer carries the date range instead of a single day. Used
// for project documentation — not exposed via the public API (lives
// under data/pdfs/weekly/).

#import "_macros.typ": *

#let data = json(bytes(sys.inputs.payload))
#let week = data.week
#let days = data.days

// ── Document-wide defaults ─────────────────────────────────────────
#set document(
  title: "Remorseless Havoc — " + week.week_label + " (" + week.week_range + ")",
  author: "Simon Roloff",
)
#set text(font: FONT_BODY_ROMAN, size: 9.2pt, fill: INK)
#set par(leading: 0.32em, justify: false)
#set heading(numbering: none)
#show heading.where(level: 1): it => small-heading-block(it.body)
#show heading.where(level: 2): it => text(
  font: FONT_HEADING_MED, weight: 500, size: 12.5pt, fill: INK,
  tracking: 0.22em,
)[#upper(it.body)]

// ── Cover (week-range footer instead of a single day) ─────────────
#cover-page(data.cover_path, week.week_label, week.week_range)

// ── Body pagination ────────────────────────────────────────────────
#counter(page).update(1)
#set page(
  paper: "a4",
  margin: (top: 32mm, bottom: 22mm, left: 28mm, right: 28mm),
  header: context {
    set text(font: FONT_MONO, size: 7pt, fill: INK_HEADER, tracking: 0.18em)
    grid(
      columns: (1fr, 1fr),
      align: (left, right),
      upper("Remorseless Havoc · " + week.week_label),
      upper(week.week_range),
    )
  },
  footer: context {
    set text(font: FONT_MONO, size: 7pt, fill: INK_HEADER, tracking: 0.18em)
    align(center, str(counter(page).at(here()).first()))
  },
)

// ── One day section: title + stats line + per-vessel poems ─────────
#let day-section(d) = [
  #pagebreak(weak: true)
  // Real level-1 heading drives the bookmark and lets us address the
  // section by date in the PDF outline. Visual rendering goes through
  // the small section-heading rule.
  = #d.stats.long_date

  #block(below: 8mm)[
    #set text(font: FONT_MONO, size: 8pt, fill: INK_RULE, tracking: 0.06em)
    #upper[
      #d.stats.vessels_active_str vessels ·
      #d.stats.stanzas_caught_str stanzas ·
      +#d.stats.depletion_pct_str% depletion
    ]
  ]

  #for poem in d.poems [
    #render-poem(poem)
  ]
]

// ── Days, in chronological order ───────────────────────────────────
#for d in days [#day-section(d)]
