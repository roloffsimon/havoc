# Stanza-Wortlisten — deutsche Adaption (Arbeitsfassung)

**Zweck:** Erste Vorschlagsspalte für die Übersetzung/Adaption der 248 Tokens
aus `backend/app/stanza.py`, die das kombinatorische Material für *Sea and
Spar Between* (Montfort/Strickland 2010) bilden. Eine deutsche Fassung der
Website soll bei aktivem `lang=de`-Toggle diese Listen statt der englischen
verwenden.

**Quellenlage der Vorschläge:**
- *Moby-Dick*-Termini orientieren sich tendenziell an **Friedhelm Rathjen**
  (2004, Zweitausendeins) — philologisch näher am Original als Jendis.
  Wo Jendis (2001) populärer ist, vermerkt.
- *Dickinson*-Anklänge orientieren sich tendenziell an **Gunhild Kübler**
  (Hanser, *Sämtliche Gedichte*, 2015), gelegentlich an **Paul Celan**
  (Auswahl) und **Werner von Koppenfels**.
- Wörtliche Übernahmen sind **nicht** verifiziert — ich habe die Bände
  nicht im Volltext vorliegen. Das hier sind tonal/stilistisch
  begründete Vorschläge, die du gegen die Druckausgaben prüfen musst.
- "(eigen)" = freier Vorschlag ohne Vorbild in einer kanonischen Übersetzung.

**Strukturelle Probleme**, die in den Anmerkungen mitlaufen:
1. **Silbenzahl** — die Listen sind nach Silben gestaffelt; deutsche
   Äquivalente sind oft länger (`eternity` 4 → *Ewigkeit* 3, aber
   `immortality` 5 → *Unsterblichkeit* 4).
2. **Genus** — `_one_noun` reiht "one X one Y…"; im Deutschen müsste
   *ein/eine/ein* mitwandern oder ganz wegfallen (Vorschlag: weglassen).
3. **`-less`-Suffix** — Dickinsons produktivstes Suffix; *-los* funktioniert
   bei manchen, bei anderen (besonders deverbalen Bildungen wie
   *efface-less*, *perturb-less*) gar nicht. Hier müsste der Generator
   `_rise_and_go` / `_but` ggf. neu gedacht werden.
4. **Komposita** — `_compound_course` baut englisch-fremde Komposita
   (*"bag-fin course"*); im Deutschen sind Komposita normal und
   verlieren genau diese Verfremdung.

---

## 1. SHORT_PHRASE (19) — kurze Imperative/Anrufe

| EN | Silben | DE-Vorschlag | Silben | Anmerkung |
|---|---|---|---|---|
| circle on | 3 | kreise nur | 3 | (eigen) — alt: *kreis nur* (3) |
| dash on | 2 | stürme nur | 3 | (eigen) — alt: *jag nur* (2) |
| let them | 2 | lass sie | 2 | (eigen) |
| listen now | 3 | horche jetzt | 3 | (eigen) — alt: *hör nun* (2) |
| loop on | 2 | schling fort | 4 | (eigen) — alt: *schling weiter* (3) |
| oh time | 2 | o Zeit | 2 | Dickinson-Anrufung (Kübler-nah) |
| plunge on | 2 | stürz fort | 3 | (eigen) |
| reel on | 2 | spul fort | 3 | (eigen) — alt: *taumle weiter* |
| roll on | 2 | roll fort | 3 | (eigen) |
| run on | 2 | renn fort | 3 | (eigen) |
| spool on | 2 | spul fort | 3 | (eigen) — kollidiert mit *reel on* |
| steady | 2 | stetig | 2 | (eigen) |
| swerve me? | 2 | mich beugen? | 3 | Moby-Dick Kap. 37, Ahab-Monolog; Rathjen: *"mich abbringen?"* — hier kürzer |
| turn on | 2 | dreh fort | 3 | (eigen) |
| wheel on | 2 | kreise fort | 3 | (eigen) — alt: *kreis weiter* |
| whirl on | 2 | wirbel fort | 4 | (eigen) |
| you -- too -- | 2 | du -- auch -- | 2 | Dickinson-Gedankenstriche, Kübler-Konvention |
| fast-fish | 2 | fester Fisch | 3 | **Rathjen** (Moby-Dick Kap. 89) |
| loose-fish | 2 | loser Fisch | 3 | **Rathjen** (Moby-Dick Kap. 89) |

---

## 2. DICKINSON_NOUN — gestaffelt nach Silbenzahl

### 2a) 1-silbig (44) — gespeist in `_one_noun` ("one X one Y one Z one W")

> **Hinweis:** Im Deutschen müsste der Artikel mitlaufen, was Genus-Probleme
> erzeugt. Vorschlag: Artikel weglassen, ggf. Bindestrich-Konstruktion
> (*"Luft Kunst Sorge Tür"* oder *"Luft – Kunst – Sorg – Tür"*).
> Generator-Funktion `_one_noun` müsste angepasst werden.

| EN | DE-Vorschlag | Silben (DE) | Genus | Anmerkung |
|---|---|---|---|---|
| air | Luft | 1 | f | |
| art | Kunst | 1 | f | |
| care | Sorg | 1 | f | poetische Kürzung von *Sorge* (Kübler-Tradition) |
| door | Tür | 1 | f | |
| dust | Staub | 1 | m | |
| each | jed | 1 | – | poetisch verkürzt; alt: *all* |
| ear | Ohr | 1 | n | |
| earth | Erd | 1 | f | poet. (Kübler) — alt: *Erde* (2) |
| fair | schön | 1 | adj | (eigen) — *fair* ist mehrdeutig |
| faith | Glaub | 1 | m | poet. (alt: *Glaube* 2) |
| fear | Furcht | 1 | f | |
| friend | Freund | 1 | m | |
| gold | Gold | 1 | n | |
| grace | Huld | 1 | f | (eigen) — alt: *Gnade* (2), *Anmut* (2) |
| grass | Gras | 1 | n | |
| grave | Grab | 1 | n | |
| hand | Hand | 1 | f | |
| hill | Höh | 1 | f | (eigen) — alt: *Hügel* (2) |
| house | Haus | 1 | n | |
| joy | Freud | 1 | f | poet. (Kübler-Tradition); alt: *Lust* |
| keep | Hut | 1 | f | (eigen) — alt: *Halt*, *Wahr* |
| leg | Bein | 1 | n | |
| might | Macht | 1 | f | |
| mind | Geist | 1 | m | (eigen) — alt: *Geist* |
| morn | Früh | 1 | f | poet. (Kübler) — alt: *Morgen* (2) |
| name | Nam | 1 | m | poet. (alt: *Name* 2) |
| need | Not | 1 | f | |
| noon | Mittag | 2 | m | **Problem** — kein 1-silbiges Äquivalent → in zweisilbige Verschieben |
| pain | Pein | 1 | f | (Kübler-nah) — alt: *Schmerz* (1, m) |
| place | Ort | 1 | m | |
| play | Spiel | 1 | n | |
| rest | Ruh | 1 | f | poet. (alt: *Rast* 1, *Ruhe* 2) |
| rose | Ros | 1 | f | poet. (alt: *Rose* 2) |
| show | Schau | 1 | f | |
| sight | Sicht | 1 | f | (eigen) — alt: *Blick* (1, m) |
| sky | Blau | 1 | n | (eigen, Celan-Anklang) — alt: *Himmel* (2) |
| snow | Schnee | 1 | m | |
| star | Stern | 1 | m | |
| thought | Sinn | 1 | m |  |
| tree | Baum | 1 | m | |
| well | Quell | 1 | m | (eigen) — alt: *Brunn* (1) |
| wind | Wind | 1 | m | |
| world | Welt | 1 | f | |
| year | Jahr | 1 | n | |

### 2b) 2-silbig (21)

| EN | DE-Vorschlag | Silben (DE) | Anmerkung |
|---|---|---|---|
| again | wieder | 2 | |
| alone | allein | 2 | |
| better | besser | 2 | |
| beyond | jenseits | 2 | (eigen) — alt: *drüben* |
| delight | Wonne | 2 | (Kübler-Tradition) |
| dying | Sterben | 2 | |
| easy | einfach | 1 |  |
| enough | genug | 2 | |
| ever | immer | 2 | |
| father | Vater | 2 | |
| flower | Blume | 2 | alt: *Blüte* |
| further | weiter | 2 | |
| himself | er selbst | 2 | |
| human | menschlich | 2 | (adj.) — als Substantiv: *Mensch* (1) |
| morning | Morgen | 2 | |
| myself | ich selbst | 2 | |
| power | Stärke | 2 | (eigen) — *Macht* (1) zu kurz |
| purple | purpurn | 2 | (Kübler-nah) — alt: *Purpur* (2) |
| single | einzig | 2 | |
| spirit | Seele | 2 |  |
| today | heute | 2 | |

### 2c) 3-silbig (2)

| EN | DE-Vorschlag | Silben (DE) | Anmerkung |
|---|---|---|---|
| another | ein andres | 3 | (eigen) |
| paradise | Paradies | 3 | |

### 2d) 4-silbig (1)

| EN | DE-Vorschlag | Silben (DE) | Anmerkung |
|---|---|---|---|
| eternity | Unendlichkeit | 4 |  |

### 2e) 5-silbig (1)

| EN | DE-Vorschlag | Silben (DE) | Anmerkung |
|---|---|---|---|
| immortality | Unsterblichkeiten | 5 |  |

---

## 3. COURSE_START (3) — leitet `_compound_course` ein

> Original-Schema: *"fix upon the [SYL][SYL] course"*.
> Im Deutschen wird das Kompositum am Ende zum Wort verschmelzen
> (*"den Sackflossenkurs"*); deshalb muss `course` direkt am Kompositum
> hängen, was den Generator umbaut.

| EN | DE-Vorschlag | Anmerkung |
|---|---|---|
| fix upon the | richte auf den | (eigen) — Akkusativ; problematisch bei f./n. (*die*/*das*) |
| cut to fit the | schneide zurecht den | (eigen) — sperrig; alt: *zuschneid* |
| how to withstand the | wie zu trotzen dem | (eigen) — Dativ; **Kasus-Inkonsistenz** zu den anderen beiden |

**Strukturentscheidung nötig:** Entweder einheitlicher Kasus (alle Akk. oder
alle Dat.), oder Generator akzeptiert pro Phrase einen Artikel-Slot.

---

## 4. SYLLABLE-Listen — Kompositionsmaterial für `_compound_course`

### 4a) DICKINSON_SYLLABLE (23)

| EN | DE-Vorschlag | Silben | Anmerkung |
|---|---|---|---|
| bard | Skald | 1 | (eigen) — alt: *Barde* (2) |
| bead | Perl | 1 | poet. — alt: *Perle* (2) |
| bee | Bien | 1 | poet. — alt: *Imm* (1, dial.) |
| bin | Trog | 1 | (eigen) |
| blot | Klecks | 1 | |
| blur | Schlier | 1 | (eigen) |
| buzz | Summ | 1 | (eigen) — onomat. |
| curl | Lock | 1 | (eigen) — alt: *Kringel* (2) |
| dirt | Dreck | 1 | alt: *Schmutz* |
| disk | Scheib | 1 | poet. — alt: *Scheibe* (2) |
| drum | Pauk | 1 | (eigen) — alt: *Trommel* (2) |
| fern | Farn | 1 | |
| film | Schleier | 2 | **Problem** — *Häut* (1) zu schief |
| folk | Volk | 1 | |
| germ | Keim | 1 | |
| hive | Stock | 1 | (eigen) — alt: *Korb* |
| hood | Haub | 1 | poet. — alt: *Kappe* (2) |
| husk | Hüls | 1 | poet. — alt: *Schale* (2) |
| jay | Häher | 2 | **Problem** — kein 1-silbiges Äquivalent |
| pink | Rosa | 2 | **Problem** — *pink* (1, Anglizismus) möglich |
| plot | Plan | 1 | (eigen) |
| spun | Garn | 1 | (eigen) — *gesponnen* zu lang |
| web | Netz | 1 | |

### 4b) MELVILLE_SYLLABLE (31)

| EN | DE-Vorschlag | Silben | Anmerkung |
|---|---|---|---|
| bag | Sack | 1 | **kollidiert mit `sack`** |
| buck | Bock | 1 | **kollidiert mit `ram`** |
| bunk | Pritsch | 1 | (eigen) — alt: *Koje* (2) |
| cane | Rohr | 1 | (eigen) |
| chap | Kerl | 1 | (eigen) |
| chop | Hieb | 1 | (eigen) — kollidiert mit *dash* |
| dash | Strich | 1 | (eigen) |
| dock | Dock | 1 | |
| edge | Schneid | 1 | (eigen) — alt: *Rand* |
| fin | Floss | 1 | poet. (Rathjen-nah) — alt: *Flosse* (2) |
| hag | Hex | 1 | poet. — alt: *Hexe* (2) |
| hawk | Falk | 1 | poet. — alt: *Habicht* (2) |
| hook | Hak | 1 | poet. — alt: *Haken* (2) |
| hoop | Reif | 1 | (eigen) |
| horn | Horn | 1 | |
| howl | Heul | 1 | poet. |
| iron | Eisen | 2 | **Silbenverlust** unvermeidlich |
| jack | Knecht | 1 | (eigen) — Moby-Dick: oft auch *Bursch* |
| jaw | Maul | 1 | Rathjen-Tradition; alt: *Kiefer* (2) |
| kick | Tritt | 1 | |
| lime | Kalk | 1 | |
| loon | Tölpel | 2 | **Silbenverlust** — alt: *Narr* (1, semantisch schief) |
| lurk | Schleich | 1 | (eigen) — alt: *Lauer* (2) |
| milk | Milch | 1 | |
| pike | Spieß | 1 | (eigen) — alt: *Hecht* (Fisch, nicht Waffe) |
| rag | Lump | 1 | (eigen) — alt: *Fetz* |
| rail | Reling | 2 | **Silbenverlust** — alt: *Schien* (1, Eisenbahn-konnotiert) |
| ram | Widder | 2 | **Silbenverlust** unvermeidlich |
| sack | Sack | 1 | **kollidiert mit `bag`** — alt: *Beutel* (2) |
| salt | Salz | 1 | |
| tool | Werk | 1 | (eigen) — alt: *Zeug* (1) |

> **Kollisionen:** `bag/sack`, `buck/ram`, `chop/dash` — im Englischen
> verschiedene Wörter, im Deutschen mit gleichem oder zu nahem Klang.
> Generator muss Duplikate vermeiden oder Liste neu kuratiert werden.

---

## 5. DICKINSON_LESS_LESS — die `-less`/`-los`-Hürde

> **Strukturproblem:** `-los` produziert idiomatische Adjektive nur bei
> Nomen (Schuld → schuldlos), nicht bei Verben oder Verbalsubstantiven
> (efface, perturb, repeal). Außerdem haben einige `-los`-Bildungen im
> Deutschen feste idiomatische Bedeutungen, die mit Dickinson kollidieren
> (*grundlos* = "ohne Grund/Anlass", nicht "ohne Sockel"; *fruchtlos* =
> "vergeblich", nicht "ohne Frucht"; *pausenlos* = "unaufhörlich").
>
> **Möglicher Ausweg:** Suffix-Wechsel auf *-fern* (Celan-Echo:
> *kunstfern, todfern*) oder *-leer* (*sinn-leer, sternleer*) — verändert
> aber den Charakter des Werks. Alternativ Generator umbauen auf
> *"ohne X"* + Verbpaar.

### 5a) 1-silbig (44)

| EN | DE-Vorschlag | `-los`-Bildung | Anmerkung |
|---|---|---|---|
| art | Kunst | kunstlos | ✓ |
| base | Grund | grundlos | ⚠ idiomatisch "ohne Anlass" |
| blame | Schuld | schuldlos | ✓ |
| crumb | Krume | krumenlos | ✗ unidiomatisch |
| cure | Heil | heillos | ✓ idiomatisch ("desolat") |
| date | Frist | fristlos | ✓ idiomatisch ("ohne Kündigungsfrist") — schief |
| death | Tod | todlos | ⚠ alt: *unsterblich* (4) |
| drought | Dürre | dürrelos | ✗ |
| fail | Fehl | fehllos | ✗ alt: *fehlerlos* (3) |
| flesh | Fleisch | fleischlos | ✓ |
| floor | Boden | bodenlos | ✓ idiomatisch ("abgründig") |
| foot | Fuß | fußlos | ✓ |
| frame | Rahmen | rahmenlos | ✓ |
| fruit | Frucht | fruchtlos | ⚠ idiomatisch "vergeblich" |
| goal | Ziel | ziellos | ✓ |
| grasp | Griff | grifflos | ⚠ alt: *unfassbar* (4) |
| guile | List | listlos | ✗ alt: *arglos* |
| guilt | Schuld | schuldlos | **kollidiert mit `blame`** |
| hue | Farb | farblos | ✓ |
| key | Schlüssel | schlüssellos | ⚠ |
| league | Bund | bundlos | ✗ |
| list | Liste | listenlos | ✗ |
| need | Not | notlos | ✗ alt: *bedürfnislos* (4) |
| note | Ton | tonlos | ✓ idiomatisch |
| pang | Pein | peinlos | ✗ alt: *schmerzlos* |
| pause | Pause | pausenlos | ⚠ idiomatisch "unaufhörlich" |
| phrase | Phrase | phrasenlos | ✗ |
| pier | Steg | steglos | ✗ |
| plash | Platsch | platschlos | ✗ |
| price | Preis | preislos | ⚠ alt: *unbezahlbar* |
| shame | Scham | schamlos | ✓ idiomatisch |
| shape | Form | formlos | ✓ |
| sight | Blick | blicklos | ✓ (Celan-Echo) |
| sound | Klang | klanglos | ✓ idiomatisch |
| star | Stern | sternlos | ✓ |
| stem | Stamm | stammlos | ⚠ |
| stint | Maß | maßlos | ✓ idiomatisch |
| stir | Regung | regungslos | ✓ idiomatisch |
| stop | Halt | haltlos | ✓ idiomatisch |
| swerve | Schwung | schwunglos | ✓ |
| tale | Mär | märlos | ✗ alt: *geschicht-los* (4) |
| taste | Geschmack | geschmacklos | ✓ idiomatisch |
| thread | Faden | fadenlos | ⚠ |
| worth | Wert | wertlos | ✓ idiomatisch |

### 5b) 2-silbig (27) — die problematische Mitte

| EN | DE-Vorschlag | `-los`-Bildung | Anmerkung |
|---|---|---|---|
| arrest | Halt | (s. 5a) | **Verbalbildung** — alt: *bann-los* |
| blanket | Decke | deckenlos | ✗ unidiomatisch |
| concern | Sorge | sorgenlos / sorglos | ✓ |
| costume | Kostüm | kostümlos | ✗ |
| cypher | Chiffre | chiffrelos | ✗ |
| degree | Grad | gradlos | ✗ |
| desire | Begehr | begehrlos | ⚠ poet. |
| dower | Mitgift | mitgiftlos | ⚠ |
| efface | Tilgung | tilgungslos | ✗ **deverbal** |
| enchant | Zauber | zauberlos | ⚠ |
| escape | Flucht | fluchtlos | ⚠ |
| fashion | Mode | modelos | ✗ |
| flavor | Würze | würzelos | ✓ alt: *würzlos* |
| honor | Ehre | ehrenlos | ✓ idiomatisch |
| kinsman | Sippe | sippenlos | ⚠ alt: *vetter-los* |
| marrow | Mark | marklos | ✓ |
| perceive | Wahrnehm | – | ✗ **deverbal, unmöglich** |
| perturb | Störung | störungslos | ✗ **deverbal** |
| plummet | Senkblei | senkbleilos | ✗ |
| postpone | Aufschub | aufschublos | ✗ **deverbal** |
| recall | Ruf | ruflos | ⚠ |
| record | Aufzeichn | – | ✗ **deverbal** |
| reduce | Minderung | – | ✗ **deverbal** |
| repeal | Widerruf | widerruflos | ✗ **deverbal** |
| report | Bericht | berichtlos | ✗ |
| retrieve | Bergung | bergungslos | ✗ **deverbal** |
| tenant | Mieter | mieterlos | ⚠ |

> **Bilanz 5b:** Mindestens 8 deverbale Bildungen (efface, perceive,
> perturb, postpone, record, reduce, repeal, retrieve) lassen sich nicht
> sinnvoll mit *-los* verbinden. Hier ist eine **Strukturentscheidung**
> fällig: entweder Liste 5b drastisch kürzen (= weniger Permutationen,
> verändert das Werk) oder Generator-Funktionen auf eine andere
> Privations­struktur umstellen.

### 5c) 3-silbig (2)

| EN | DE-Vorschlag | `-los`-Bildung | Anmerkung |
|---|---|---|---|
| latitude | Breitengrad | – | ✗ **kein `-los`** möglich; alt: *grenzen-los* (4) |
| retriever | Apportier | – | ✗ Hund / **deverbal**; alt: *bergungs-los* |

---

## 6. UP_VERB (12) — Verbpaare in `_rise_and_go`

> Schema: *"X-less Y and Z"* → *"Xlos Y und Z"*. Im Deutschen
> Infinitive (oder bare Stems wie Englisch), gepaart durch *und*.

| EN | DE-Vorschlag | Anmerkung |
|---|---|---|
| bask | sonnen | (sich sonnen — reflexiv stört Generator) |
| chime | klingen | alt: *läuten* |
| dance | tanzen | |
| go | gehen | |
| leave | scheiden | (eigen) — alt: *lassen* |
| move | regen | (eigen) — alt: *ziehen* |
| rise | steigen | |
| sing | singen | |
| speak | sprechen | |
| step | schreiten | |
| turn | wenden | alt: *kehren* |
| walk | wandeln | (Kübler-Tonfall) — alt: *gehen* (kollidiert) |

---

## 7. BUT_BEGINNING (3) + BUT_ENDING (4) — `_but`

Schema: *"but X-less is the Y"* → *"doch Xlos ist die/der/das Y"*.

### 7a) BUT_BEGINNING

| EN | DE-Vorschlag | Anmerkung |
|---|---|---|
| but | doch | alt: *aber* (2) |
| for | denn | |
| then | dann | |

### 7b) BUT_ENDING

| EN | DE-Vorschlag | Genus | Anmerkung |
|---|---|---|---|
| earth | Erde | f | |
| sea | See | f | **Rathjen** bevorzugt *See* gegen Jendis' *Meer* |
| sky | Himmel | m | |
| sun | Sonne | f | |

> **Genus-Problem:** Original *"is the X"* → im Deutschen *"ist die Erde / die See / der Himmel / die Sonne"*. Generator muss pro Token den Artikel mitführen.

---

## 8. NAILED_ENDING (11) — `_nailed`

Schema: *"nailed to the X"* → *"genagelt an die/den/das X"*. Bezugsstelle: Doublonen-Szene Moby-Dick Kap. 36 (*"This was the Spanish ounce of gold worth sixteen dollars … nailed to the mast"*).

| EN | DE-Vorschlag | Genus | Anmerkung |
|---|---|---|---|
| coffin | Sarg | m | (Rathjen / Jendis übereinstimmend) |
| deck | Deck | n | |
| desk | Pult | n | (eigen) — alt: *Tisch* |
| groove | Furche | f | (eigen) — alt: *Rille* |
| mast | Mast | m | |
| spar | Spiere | f | **Rathjen**; Jendis: *Rah* |
| pole | Pfahl | m | alt: *Stange* (f) |
| plank | Planke | f | |
| rail | Reling | f | |
| room | Kammer | f | (eigen) — alt: *Raum* (m) |
| sash | Schärpe | f | **mehrdeutig** — *sash* = auch Fenster­sprosse; Kontext Moby-Dick? prüfen |

---

## 9. Aufgaben & offene Entscheidungen (Zusammenfassung)

1. **Generator-Funktionen anpassen:**
   - `_one_noun` — Artikel-Behandlung (weglassen vs. mitführen)
   - `_compound_course` — Artikel-Slot pro `COURSE_START`-Phrase
   - `_but` — Genus-bewusster Artikel vor `BUT_ENDING`
   - `_nailed` — wie `_but`
   - `_rise_and_go` — `-los`-Bildung oder Strukturwechsel

2. **`-less`-Privation grundsätzlich klären:**
   - Variante A: nur idiomatische `-los`-Bildungen zulassen (Liste 5b
     auf ~8 Tokens schrumpfen) → kleineres kombinatorisches Raum
   - Variante B: Suffix-Wechsel zu *-fern* / *-leer* (poetisch, aber
     verschiebt das Werk Richtung Celan)
   - Variante C: Konstruktionswechsel zu *"ohne X"* — bricht Versmaß

3. **Kanonische Übersetzungen verifizieren:**
   - Rathjen *Moby-Dick*: Kap. 36 (*nailed to the mast*), Kap. 37
     (*swerve me*), Kap. 89 (*fast-fish/loose-fish*)
   - Kübler *Dickinson sämtliche Gedichte*: Bestätigung der
     Tonfall-Wahl bei *Pein, Wonne, Früh, Glaub, Ros*
   - Celan *Übersetzungen* (Auswahl Dickinson): falls *du -- auch --*
     dort vorkommt

4. **Kollisionen auflösen:** `bag/sack`, `buck/ram`, `chop/dash`,
   `Schuld` (5a `blame` / 5b `guilt`), `Sinn` (2a `mind` / `thought`).

5. **Silbenverluste quantifizieren:** in 2d/2e und an Einzelstellen
   in Liste 4 — entscheiden, ob die metrische Staffelung
   (1→2→3→4→5) im Deutschen aufgeweicht oder neu kalibriert wird.

---

*Datei: `generation/Stanza_DE_Uebersetzung.md` — Stand 2026-04-25*
