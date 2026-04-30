"""Beispielstrophen aus dem deutschen Generator.

Aufruf aus dem Projektroot:
    python3 generation/demo_stanza_de.py

Die Auswahl deckt alle 4×4 = 16 Erst-/Zweit-Zeilen-Kombinationen ab
(jede Zeilenfunktion mehrfach), plus ein paar weit gestreute
Lattice-Punkte zur Sichtprüfung.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.stanza_de import (  # noqa: E402
    generate_stanza,
    _first_line,
    _second_line,
)


def show(i: int, j: int) -> None:
    print(f"--- (i={i}, j={j}) — Erste Zeile-Typ: r={(i + (2 * j) + 1) % 4}, "
          f"Zweite Zeile-Typ: r={(abs(i - 2 * j) + 1) % 4} ---")
    for line in generate_stanza(i, j):
        print(line)
    print()


# Eine Reihe sorgsam gewählter (i, j), die alle 16 Kombinationen
# durchschlagen. Indem wir i über 0..3 und j über 0..3 fahren, bekommen
# wir alle Modulo-4-Kombinationen für Erst- und Zweit-Zeile.
COORDS_GRID = [(i, j) for j in range(4) for i in range(4)]

# Zusätzliche, weit gestreute Punkte zur Sichtung der Vokabular-Vielfalt.
COORDS_RANDOM = [
    (7, 7), (12, 17), (23, 41), (100, 200),
    (1234, 5678), (999_999, 1_234_567),
]


print("=" * 70)
print("Systematisches 4×4-Raster (alle Zeilen-Kombinationen):")
print("=" * 70 + "\n")
for i, j in COORDS_GRID:
    show(i, j)

print("=" * 70)
print("Weit gestreute Lattice-Punkte:")
print("=" * 70 + "\n")
for i, j in COORDS_RANDOM:
    show(i, j)

# Zusatzdiagnose: einzelne Zeilen-Funktionen direkt durchspielen.
print("=" * 70)
print("Zeilen-Funktionen direkt (n = 0..7 für jede):")
print("=" * 70 + "\n")
for label, n_range in [("_first_line", range(8)), ("_second_line", range(8))]:
    print(f"# {label}")
    fn = _first_line if label == "_first_line" else _second_line
    for n in n_range:
        print(f"  n={n}: {fn(n)}")
    print()
