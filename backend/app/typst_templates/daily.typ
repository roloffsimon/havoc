// daily.typ — one day's "Catch of the Day" volume.
//
// Reads its data from `sys.inputs.payload` (a JSON blob set by
// typst_renderer.render). Sections in order: cover, TOC, introduction,
// section opener, per-vessel poems, index of vessels, colophon.

#import "_macros.typ": *

#let data = json(bytes(sys.inputs.payload))
#let stats = data.stats
#let poems = data.poems

// ── Document-wide defaults ─────────────────────────────────────────
#set document(
  title: "Catch of the Day — " + stats.long_date,
  author: "Simon Roloff",
)
#set text(font: FONT_BODY_ROMAN, size: 9.2pt, fill: INK)
#set par(leading: 0.32em, justify: false)
#set heading(numbering: none)

// Visual rendering for headings. Level 1 = section heads. The Section
// Opener "Catch of Day NNN" gets the big centered display style; the
// other four (Contents, Introduction, Index, Colophon) get the small
// block style. We branch on the heading's label.
#show heading.where(level: 1): it => context {
  let so = query(<section-opener>)
  if so.len() > 0 and so.first().location() == it.location() [
    #align(center)[
      #set text(font: FONT_HEADING_MED, weight: 500, size: 22pt,
                fill: INK, tracking: 0.22em)
      #it.body
    ]
  ] else [
    #small-heading-block(it.body)
  ]
}

// Level 2 = vessel name in each poem. Render inline so the flag span
// in render-poem can sit on the same baseline.
#show heading.where(level: 2): it => text(
  font: FONT_HEADING_MED, weight: 500, size: 12.5pt, fill: INK,
  tracking: 0.22em,
)[#upper(it.body)]

// ── Cover ──────────────────────────────────────────────────────────
#cover-page(data.cover_path, stats.day_label, stats.long_date)

// ── Body pagination: reset the page counter, set running header/footer
#counter(page).update(1)
#set page(
  paper: "a4",
  margin: (top: 32mm, bottom: 22mm, left: 28mm, right: 28mm),
  header: context {
    set text(font: FONT_MONO, size: 7pt, fill: INK_HEADER, tracking: 0.18em)
    grid(
      columns: (1fr, 1fr),
      align: (left, right),
      upper("Catch of Day " + stats.day_label),
      upper(stats.long_date),
    )
  },
  footer: context {
    set text(font: FONT_MONO, size: 7pt, fill: INK_HEADER, tracking: 0.18em)
    align(center, str(counter(page).at(here()).first()))
  },
)

// ── Front matter ───────────────────────────────────────────────────
#toc(stats)
#about(stats)
#section-opener(stats.day_label)

// ── Per-vessel poems ───────────────────────────────────────────────
#for poem in poems [
  #render-poem(poem)
]

// ── Index of vessels ───────────────────────────────────────────────
#pagebreak()
#vessel-index(poems)

// ── Colophon ───────────────────────────────────────────────────────
#colophon(stats)
