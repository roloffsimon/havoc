# Generation — *Remorseless Havoc*

Dieser Ordner dokumentiert, wie der poetische Ozean der Website generiert und wie er durch reale Fischerei gelöscht wird. Er ist **nicht Teil des Website-Deployments**, sondern dient der Transparenz der Generierungs- und Löschungslogik.

Stand: v5 Night Graphite (April 2026).

---

## Inhalt

| Datei | Rolle |
|---|---|
| `HAVOC_Demo_v3.ipynb` | Vollständiges Demo-Notebook: Port des *Sea and Spar Between*-Generators, Ozean-Mapping, Landmaske, Depletion-Simulation, PDF-Assembly. |
| `generate_display_mask.py` | Produziert die im Frontend verwendete Binärmaske `land_mask_3600x1800.bin` (3.600 × 1.800, 0,1°). |
| `ocean_mask.npz` | Backend-Auflösung der Ozeanmaske (18.000 × 36.000 Zellen, 0,01°), als NumPy-NPZ gepackt. |
| `mask_reference.png` | Visuelle Referenz der generierten Landmaske zur Sichtprüfung. |
| `events_2026-02-24.json` | Beispiel-Dump eines GFW-Events-API-Tagesabrufs (Testdaten für den Depletion-Algorithmus). |
| `erosion_by_year.json` | Aggregierte jährliche Fischereistunden pro Region — Grundlage für Depletionsabschätzungen. |
| `Konzepttext Website.md` | Aktueller Konzepttext der Website (DE/EN), wie er im „About"-View der Website erscheint. |
| `_Webtext_Briefing_source.md` | Ausgangstext, aus dem dieses README entstanden ist. |

---

## 1. Ausgangspunkt: *Sea and Spar Between* (Montfort / Strickland, 2010)

- Kombinatorischer Stanzengenerator im Browser, aus Wortmaterial Emily Dickinsons und Herman Melvilles.
- Toroidales Lattice von **14.992.384 × 14.992.384** Positionen → ca. **225 Billionen** Stanzen.
- Jede Position `(i, j)` produziert **deterministisch** immer dieselbe 4-Zeilen-Stanze (zwei Couplets).
- Code steht unter BSD-Lizenz. Python-Port des Originalgenerators im Notebook (Cell 1), verbatim aus dem Original-JavaScript.

## 2. Erste Löschung: Ozean-Mapping

**Schritt A — Weltgitter anlegen.** Die Erdoberfläche wird in **0,01° × 0,01°**-Zellen unterteilt (am Äquator ≈ 1,1 × 1,1 km). Das entspricht exakt der nativen Auflösung von Global Fishing Watch (`cell_ll_lat` / `cell_ll_lon`).

- 360° ÷ 0,01° = **36.000 Spalten**
- 180° ÷ 0,01° = **18.000 Zeilen**
- Gesamt: **648.000.000 Zellen**

**Schritt B — Lattice → Gitter.** Lineares, proportionales Mapping der 14.992.384² Lattice-Positionen auf die 36.000 × 18.000 Gitterzellen:

```python
i = int(col * (LATTICE_SIZE - 1) / (GRID_COLS - 1))
j = int(row * (LATTICE_SIZE - 1) / (GRID_ROWS - 1))
```

Das Lattice ist pro Achse ~417× größer als das Gitter — Kollisionen ausgeschlossen, jede Zelle bekommt eine einzigartige, deterministisch generierte Stanze. Die massive Reduktion von 225 Bio. auf 648 Mio. ist die **erste Löschung**.

**Schritt C — Landmaske.** Mit dem Python-Package `global-land-mask` (NOAA GLOBE, ~1 km) wird für jede Zelle geprüft: Wasser oder Land? Ergebnis: Boolean-Array (18.000 × 36.000), Seen gelten als Land. Das entfernt ~29 % der Zellen. Übrig bleiben **~460.000.000 Wasserzellen = 460 Mio. lebende Stanzen**.

Für das Frontend wird die Maske auf 3.600 × 1.800 (0,1°) heruntergesampelt und als Binärdatei ausgeliefert (`website/public/land_mask_3600x1800.bin`, 6,2 MB) — produziert durch `generate_display_mask.py`.

## 3. Zweite Löschung: Fischerei als Depletion-Algorithmus

- **Datenquelle:** GFW Events API v3 (AIS-Signale → ML-Klassifikation „fishing vs. transit"), täglicher Abruf mit ~72 h Verzug.
- **GPS → Gitter:** `col = int((lon + 180) / 0.01)`, `row = int((lat + 90) / 0.01)` — identisch zur GFW-Konvention, kein Umrechnungsverlust.
- **Kernregel:** `1 Fishing Hour = 3 Stanzen` (`DEPLETION_FACTOR = 3.0`).
- **Herleitung des Faktors 3.** Der empirische Abgleich zwischen Events API (konservativ, nur hochkonfidente Events) und 4Wings Stats API (alle AIS-Fischerei-Positionen) zeigt, dass die 4Wings-API für denselben Zeitraum rund **3,4×** mehr Aufwand meldet — die Events API lässt entsprechend viel unregistriert. Wir runden diesen Korrekturfaktor bewusst auf **3,0** ab: das kostet etwa ein halbes Jahr zusätzliche Laufzeit und ~3 %-Punkte jährlicher Depletion gegenüber der scharfen Kalibrierung, schenkt aber einen Satz, der die Regel ohne Fußnote trägt — *eine Fangstunde löscht drei Strophen*. Die 4Wings-Basis bleibt als Begründung im Text stehen, damit die Zahl nicht beliebig wirkt.
- **Verteilung der Löschungen pro Event:** Die **erste** Stanze wird an der GPS-Position gelöscht (geographisch gebunden), die restlichen ziehen aus einem **globalen Cursor-Pool** (`OceanPool`), der sich systematisch durch alle noch lebenden Wasserzellen bewegt. In bereits leergefischten Gewässern greift der Cursor von der ersten Stunde an.
- **Output je Schiff:** Aus den gefangenen Stanzen wird pro Schiff und Tag ein Gedicht zusammengefügt, sortiert nach absteigender Shannon-Entropie (lexikalische Diversität). Die Tagesausgabe aller Schiffe bildet das „Catch of the Day"-PDF.

## 4. Aktuelle Website-Logik (Frontend, v5 Night Graphite)

- **Canvas-Renderer, kein Leaflet.** Eigenes Pan/Zoom, Longitude-Wrapping, Land-Mip-Map-Pyramide.
- **Farbschema:** fast schwarzes Nachtblau (Ozean), hellgraues Land, gelbe Vessel-Punkte, warmes Orange als Catch-Flash.
- **Zoom-Stufen (`ZOOM_THRESHOLDS`):**
  - `cellWidth ≥ 3 px` → Gitterlinien werden sichtbar (Alpha steigt mit Zoom)
  - `cellWidth ≥ 12 px` → Stanzen werden **in die Zellen** gezeichnet (DM Mono 300 italic, 4 Zeilen)
  - `cellWidth ≥ 40 px` → volle Lesbarkeit
- **Stanzengenerierung:** vollständiger JavaScript-Port von *Sea and Spar Between* (`generateStanza`, `gridToLattice`) — deterministisch pro Backend-Zelle, byte-identisch zum Python-Backend (`backend/app/stanza.py`). Der Generator steht unverschleiert im HTML-Quelltext, weil die Übernahme des Codes Teil der Arbeit ist.
- **Anzeige-Kacheln vs. Strophen-Zellen:** Das Backend-Gitter hat 648 Mio. Zellen (0,01°, ≈1 × 1 km). Für das Rendering im Browser werden diese zu 3 600 × 1 800 Anzeige-Kacheln aggregiert (0,1°, ≈10 × 10 km); jede sichtbare Kachel fasst also 100 Strophen-Zellen zusammen. Eine Kachel zeigt im Zoom eine einzige, stellvertretende Strophe aus ihrer zentralen Zelle (`dcol*10+5, drow*10+5`).
- **Drei Farbzustände der Kacheln:**
  - **intakt** — alle 100 Strophen der Kachel noch lebendig (Ozeanblau)
  - **teilweise abgebaut** — mindestens eine Strophe gelöscht (Übergangston)
  - **vollständig abgebaut** — alle 100 Strophen verbraucht (fast schwarz)

  Die Bitmap unter `GET /api/depletion-grid` liefert für jede Anzeige-Kachel ein Bit (`1 = in der Kachel lebt noch mindestens eine Strophe-Zelle`); eine feinere Unterscheidung zwischen "intakt" und "teilweise abgebaut" kann später aus einer 2-Bit-Packung folgen.
- **Ships:** werden aus `GET /api/vessels` geladen (Tages-Aggregat der letzten GFW-Events). Ohne Backend fällt die Karte auf eine kleine statische Demo-Flotte zurück.
- **Views:** OCEAN, FLEET, ABOUT, CATCH (PDF-Download). Das Melville-Zitat („so remorseless a havoc … final puff") liegt in v5 als **Intro-Splash** vor dem Einstieg in den Ozean. Die separate **Final View** für den Endzustand ist konzeptuell vorgesehen, im v5-Prototyp aber noch nicht aktiv implementiert (nur die Farbvariable `stanzaFinal: #22d3ee` ist vorhanden).
- **Hover:** Koordinaten + Stanze der Zelle unter dem Cursor.
- **CRT/Scanline-Effekt:** CSS-`::after` mit `repeating-linear-gradient` + Vignette.

## 5. Die letzte Zelle: „final puff"

Der Ozean wird **nicht** restlos geleert: Per Konvention bleibt **genau eine** Wasserzelle übrig — die letzte lebende Stanze des Projekts. Sobald der Pool auf `remaining == 1` fällt, greift der Depletion-Algorithmus nicht mehr zu; die letzte Zelle ist geschützt und bildet den End- und Ruhezustand der Arbeit.

- **Backend-Regel:** `OceanPool.process_event` hält einen Floor von 1. Ist nur noch eine Zelle lebendig, wird kein weiteres Fishing Event mehr in eine Löschung übersetzt. Der Cursor terminiert, das Projekt kommt zum Stillstand.
- **Frontend-Signal (konzeptuell, in v5 noch nicht aktiv):** Bei `remaining ≤ 1` wechselt das Interface in eine **Final View**. Die übriggebliebene Stanze wird zentral und groß dargestellt, in cyan-leuchtender Typografie (`stanzaFinal: #22d3ee`), flankiert vom vollständigen Melville-Zitat aus *Moby-Dick*, Kap. CV („Whether Leviathan can long endure so wide a chase, and so remorseless a havoc …").
- **Dramaturgisch:** Die letzte Zelle ist der „final puff" — der titelgebende Rest, das, was übrig bleibt, wenn die industrielle Extraktion durch ist. Sie ist die Gegenfigur zur rechnerischen Unendlichkeit des Ausgangsmaterials: aus 225 Bio. möglichen Stanzen wird **eine** bleiben.
- **Position im Gitter:** zufällig — bestimmt allein durch die reale Reihenfolge, in der GPS-Treffer und Cursor-Pool die 460 Mio. Wasserzellen verbraucht haben. Welche Stanze übrig bleibt und wo sie geographisch liegt, ist erst am Ende bekannt.

## 6. Kennzahlen

| Größe | Wert |
|---|---|
| Lattice *Sea and Spar Between* | 14.992.384 × 14.992.384 (~225 Bio. Stanzen) |
| Weltgitter | 36.000 × 18.000 = 648 Mio. Zellen (0,01°) |
| Wasserzellen nach Landmaske | ~460 Mio. (71 %) |
| Depletionsfaktor | 3 Stanzen / Fishing Hour |
| Fishing Hours/Jahr (Events API) | ~37,7 Mio. |
| Effektive Stanzen/Jahr | ~113 Mio. (37,7 × 3) |
| Depletion/Jahr | ~24,6 % |
| Geschätzte Lebensdauer | ~4 Jahre |

## 7. Konzeptueller Kern

Die Website macht in drei aufeinander aufbauenden Löschungen sichtbar, wie die rechnerische Unendlichkeit des Digitalen (225 Bio. Stanzen) schrittweise in Endlichkeit überführt wird: erstens durch das Koordinatengitter (→ 648 Mio.), zweitens durch die Landmaske (→ 460 Mio.), drittens durch die reale industrielle Fischerei, die über AIS-Daten Stunde um Stunde Stanzen konsumiert — bis **eine einzige** übrig bleibt: der „final puff", die letzte Zelle des poetischen Ozeans.

---

## Reproduzieren

```bash
# Landmaske fürs Frontend neu erzeugen
pip install global-land-mask numpy
python generate_display_mask.py
# → schreibt public/land_mask_3600x1800.bin (6,2 MB)
```

Für das vollständige Ozean-Mapping und die Depletion-Simulation: `HAVOC_Demo_v3.ipynb` von oben nach unten ausführen. Abhängigkeiten siehe erste Notebook-Zelle.
