"""
Stanza-Generator (deutsche Adaption) — Sea and Spar Between auf Deutsch.

======================================================================
  Konzeptueller Anker
======================================================================

Parallel zu `stanza.py` (Port der englischen Originalvorlage von
Montfort/Strickland 2010) liefert dieses Modul eine deutsche Fassung
für die DE-Variante der Website. Die Listenlängen sind identisch zum
Original, sodass die Lattice-Koordinate (i, j) hier auf dieselbe
Strophen-Position zugreift wie in `stanza.py` — die Depletion-Mechanik
("eine Zelle = eine Strophe") bleibt damit erhalten, nur das
Sprachmaterial wechselt.

Wortmaterial: aus `generation/Übersetzung/Stanza_DE_Uebersetzung.md`,
Spalte „DE-Vorschlag (Kontext)". Anpassungen der Generatorfunktionen
folgen den dort dokumentierten Strukturentscheidungen:
- Genus-Artikel in `_one_noun`, `_but`, `_nailed`
- Zirkumposition + Kompositum in `_compound_course`
- vorgebildete Privationsformen (-los / -fern / -frei / un...bar)
  in `DICKINSON_LESS_LESS`

Bekannte Kompromisse:
- NOUN[4] (nominell 5-silbig) enthält das 4-silbige „Unsterblichkeit".
- NOUN[0] enthält das 2-silbige `Mittag` und `Gedank` (aus Kontext-
  Spalte; keine 1-silbigen Alternativen).
- SYLLABLE-Buckets enthalten Einträge in Kompositum-Stammform (oblique
  Kasus / Fugen-n), nicht in Nominativ-Singular. Das ist notwendig, weil
  N-Deklination und Pluralia-Tantum nur in der obliquen Stammform ins
  Kompositum eingehen (*Bienenstock*, *Hexenkessel*, *Falkenauge*,
  *Hülsenfrucht*, *Lumpenproletariat*). Liste der nominell 1-silbigen
  Einträge, die so 2-silbig sind:
  - Stammform mit -en/-n (Kasus-bedingt): Bienen, Scheiben, Hauben,
    Hülsen, Pritschen, Flossen, Hexen, Falken, Haken, Lumpen, Narren
  - 2-silbig, weil keine 1-silbige Alternative existiert: Häher, Eisen,
    Reling, Kringel, Gesumm, Geheul, Beutel
  `_compound_course` zieht flach aus dem 54-er-Pool, die syllabische
  Streuung ist kosmetisch.
- `klanglos` erscheint zweimal in LESS_LESS[0] (für plash und sound),
  Doppelung aus Kontext-Spalte hingenommen.
======================================================================
"""

from .grid import LATTICE_SIZE, grid_to_lattice


# ── WORTLISTEN (Kontext-Spalte aus Stanza_DE_Uebersetzung.md) ────────

SHORT_PHRASE = [
    'kreise weiter', 'voran nun', 'lass sie', 'horch nun', 'windet euch',
    'o Zeit', 'hinab nun', 'taumle nur', 'rolle nur', 'jag nur',
    'spinn weiter', 'stetig', 'mich aufhalten?', 'wend dich', 'kreis nur',
    'wirble nur', 'du -- auch --', 'fester Fisch', 'freier Fisch',
]

# DICKINSON_NOUN[0]: (Artikel, Wort) — Artikel ist None für genus-lose
# Einträge ('je' = each/distributiv, 'hell' = adj). Reihenfolge wie EN
# (identische Lattice-Indizes pro Position).
DICKINSON_NOUN = [
    [
        ('eine', 'Luft'), ('eine', 'Kunst'), ('eine', 'Sorg'),
        ('eine', 'Tür'), ('ein', 'Staub'), (None, 'je'),
        ('ein', 'Ohr'), ('eine', 'Erd'), (None, 'hell'),
        ('ein', 'Glaub'), ('eine', 'Furcht'), ('ein', 'Freund'),
        ('ein', 'Gold'), ('eine', 'Huld'), ('ein', 'Gras'),
        ('ein', 'Grab'), ('eine', 'Hand'), ('eine', 'Höh'),
        ('ein', 'Haus'), ('eine', 'Freud'), ('ein', 'Hut'),
        ('ein', 'Bein'), ('eine', 'Macht'), ('ein', 'Sinn'),
        ('eine', 'Früh'), ('ein', 'Nam'), ('eine', 'Not'),
        ('ein', 'Mittag'), ('eine', 'Pein'), ('ein', 'Ort'),
        ('ein', 'Spiel'), ('eine', 'Ruh'), ('eine', 'Ros'),
        ('eine', 'Schau'), ('ein', 'Blick'), ('ein', 'Blau'),
        ('ein', 'Schnee'), ('ein', 'Stern'), ('ein', 'Gedanke'),
        ('ein', 'Baum'), ('ein', 'Quell'), ('ein', 'Wind'),
        ('eine', 'Welt'), ('ein', 'Jahr'),
    ],
    ['wieder', 'allein', 'besser', 'jenseits', 'Wonne', 'Sterben',
     'leichthin', 'genug', 'immer', 'Vater', 'Blume', 'ferner',
     'er selbst', 'menschlich', 'Morgen', 'ich selbst', 'Gewalt',
     'purpurn', 'einzig', 'Geist', 'heute'],
    ['ein andres', 'Paradies'],
    ['Ewigkeit'],
    ['Unsterblichkeit'],
]

# (Präfix, Suffix) — einheitlich Akkusativ; Kompositum wird in den Slot
# zwischen Präfix und Suffix eingesetzt.
COURSE_START = [
    ('auf den ', ' versessen'),
    ('auf den ', ' zugerichtet'),
    ('wie den ', ' zu bestehen'),
]

DICKINSON_SYLLABLE = [
    'Skald', 'Perl', 'Bienen', 'Trog', 'Klecks', 'Schlier', 'Gesumm',
    'Kringel', 'Schmutz', 'Scheiben', 'Trumm', 'Farn', 'Haut', 'Volk',
    'Keim', 'Stock', 'Hauben', 'Hülsen', 'Häher', 'Pink', 'Plan', 'Garn',
    'Netz',
]

MELVILLE_SYLLABLE = [
    'Sack', 'Stier', 'Pritschen', 'Stab', 'Kerl', 'Schlag', 'Strich',
    'Dock', 'Schneid', 'Flossen', 'Hexen', 'Falken', 'Haken', 'Reif',
    'Horn', 'Geheul', 'Eisen', 'Hein', 'Maul', 'Tritt', 'Kalk', 'Narren',
    'Schleich', 'Milch', 'Spieß', 'Lumpen', 'Reling', 'Bock', 'Beutel',
    'Salz', 'Zeug',
]

SYLLABLE = sorted(DICKINSON_SYLLABLE + MELVILLE_SYLLABLE)

# Vorgebildete Privationsformen — keine on-the-fly-Suffigierung mehr.
DICKINSON_LESS_LESS = [
    ['kunstlos', 'standlos', 'schuldfrei', 'brotlos', 'heillos',
     'fristfern', 'todesfern', 'dürrefern', 'fehlfrei', 'fleischfern',
     'bodenlos', 'fußlos', 'rahmenlos', 'fruchtlos', 'ziellos',
     'unfasslich', 'arglos', 'reuelos', 'farblos', 'schlüssellos',
     'bundlos', 'listenlos', 'notfrei', 'tonlos', 'schmerzlos',
     'pausenlos', 'wortlos', 'steglos', 'klanglos', 'preislos',
     'schamlos', 'gestaltlos', 'blicklos', 'klanglos', 'sternlos',
     'wurzellos', 'maßlos', 'regungslos', 'haltlos', 'unaufhaltsam',
     'märlos', 'geschmacklos', 'fadenlos', 'wertlos'],
    ['bannfrei', 'deckenlos', 'sorglos', 'kostümlos', 'chiffrelos',
     'gradlos', 'begehrlos', 'mitgiftlos', 'löschfern', 'zauberlos',
     'fluchtlos', 'modelos', 'würzlos', 'ehrlos', 'sippenlos',
     'marklos', 'unmerklich', 'unstörbar', 'grundlos', 'unaufschiebbar',
     'unrufbar', 'spurlos', 'unverminderbar', 'unwiderruflich',
     'berichtlos', 'ungeborgen', 'mieterlos'],
    ['breitenlos', 'unwiederbringlich'],
]

DICKINSON_FLAT_LESS_LESS = sorted(
    DICKINSON_LESS_LESS[0] + DICKINSON_LESS_LESS[1] + DICKINSON_LESS_LESS[2]
)

UP_VERB = ['sonnen', 'läuten', 'tanzen', 'gehen', 'scheiden', 'regen',
           'steigen', 'singen', 'sprechen', 'schreiten', 'wenden',
           'wandeln']

BUT_BEGINNING = ['doch', 'denn', 'dann']

# (Artikel-Nominativ, Substantiv) — "ist die/der/das X"
BUT_ENDING = [
    ('die', 'Erde'), ('die', 'See'), ('der', 'Himmel'), ('die', 'Sonne'),
]

THREE_TO_FIVE_SYLLABLE = (
    DICKINSON_NOUN[2] + DICKINSON_NOUN[3] + DICKINSON_NOUN[4]
    + DICKINSON_LESS_LESS[2]
)
TWO_SYLLABLE = DICKINSON_NOUN[1] + DICKINSON_LESS_LESS[1]

# (Akkusativ-Artikel, Substantiv) — "an die/den/das X"
NAILED_ENDING = [
    ('den', 'Sarg'), ('das', 'Deck'), ('das', 'Pult'),
    ('die', 'Furche'), ('den', 'Mast'), ('die', 'Spiere'),
    ('den', 'Pfahl'), ('die', 'Planke'), ('die', 'Reling'),
    ('die', 'Kammer'), ('die', 'Schärpe'),
]


# ── Listenlängen-Sanity (fängt Tippfehler beim Eintragen) ────────────

assert len(SHORT_PHRASE) == 19
assert [len(b) for b in DICKINSON_NOUN] == [44, 21, 2, 1, 1]
assert len(COURSE_START) == 3
assert len(DICKINSON_SYLLABLE) == 23
assert len(MELVILLE_SYLLABLE) == 31
assert [len(b) for b in DICKINSON_LESS_LESS] == [44, 27, 2]
assert len(UP_VERB) == 12
assert len(BUT_BEGINNING) == 3
assert len(BUT_ENDING) == 4
assert len(NAILED_ENDING) == 11


# ── Zeilen-Generatoren ───────────────────────────────────────────────

def _short(n):
    return SHORT_PHRASE[n % len(SHORT_PHRASE)]


def _render_noun(entry):
    art, word = entry
    return word if art is None else f'{art} {word}'


def _one_noun(n):
    L = len(DICKINSON_NOUN[0])
    d = n % L; n //= L
    c = n % L; n //= L
    b = n % L; n //= L
    a = n % L
    entries = [DICKINSON_NOUN[0][i] for i in (a, b, c, d)]
    # Em-Dashes zwischen den Phrasen — Dickinson-Schriftbild, das die
    # Verklumpung der vier Artikel-Wort-Paare auflöst. Sonderfall:
    # artikellose Einträge (`je` distributiv, `hell` adjektivisch)
    # binden sich an den folgenden Slot — der Em-Dash zwischen ihnen
    # und dem nächsten Wort wird durch ein einfaches Leerzeichen
    # ersetzt, sodass das Wort als Quantor bzw. Attribut zur nächsten
    # Nomenphrase läuft (*je ein Mittag*, *hell ein Stern*). Steht ein
    # artikelloser Eintrag im letzten Slot, fehlt ein nächster zum
    # Binden; er bleibt dann allein am Zeilenende stehen.
    parts: list[str] = []
    for i, entry in enumerate(entries):
        if i > 0:
            prev_artikel = entries[i - 1][0]
            parts.append(' ' if prev_artikel is None else ' -- ')
        parts.append(_render_noun(entry))
    return ''.join(parts)


def _compound_course(n):
    c = n % len(SYLLABLE); n //= len(SYLLABLE)
    b = n % len(SYLLABLE); n //= len(SYLLABLE)
    a = n % len(COURSE_START)
    # Wiederholungen wie "Beutelbeutelkurs" vermeiden: bei b==c den
    # zweiten Index deterministisch um 1 verschieben (toroidal).
    if b == c:
        c = (c + 1) % len(SYLLABLE)
    prefix, suffix = COURSE_START[a]
    head = SYLLABLE[b]               # Großschreibung erhalten (Substantiv-Anfang)
    syl_c = SYLLABLE[c]
    # Bindestrich bei Konsonantenkollision an den Komposita-Nähten;
    # nach einem Bindestrich bleibt das folgende Glied großgeschrieben
    # (DE-Orthographie: hyphenierte Komposita kapitalisieren alle
    # Teile), ohne Bindestrich wird das innere Glied kleingeschrieben.
    if head[-1:].lower() == syl_c[:1].lower():
        sep_inner, tail = '-', syl_c
    else:
        sep_inner, tail = '', syl_c.lower()
    if tail[-1:].lower() == 'k':
        sep_outer, kurs = '-', 'Kurs'
    else:
        sep_outer, kurs = '', 'kurs'
    return f'{prefix}{head}{sep_inner}{tail}{sep_outer}{kurs}{suffix}'


def _first_line(n):
    m, r = divmod(n, 4)
    if r < 2:
        return _short(m)
    if r == 2:
        return _one_noun(m)
    return _compound_course(m)


def _rise_and_go(n):
    c = n % len(UP_VERB); n //= len(UP_VERB)
    b = n % len(UP_VERB); n //= len(UP_VERB)
    a = n % len(DICKINSON_FLAT_LESS_LESS)
    privation = DICKINSON_FLAT_LESS_LESS[a]
    dash = ' --' if privation in DICKINSON_LESS_LESS[0] else ''
    return privation + ' ' + UP_VERB[b] + ' und ' + UP_VERB[c] + dash


def _but(n):
    c = n % len(BUT_ENDING); n //= len(BUT_ENDING)
    b = n % len(DICKINSON_FLAT_LESS_LESS); n //= len(DICKINSON_FLAT_LESS_LESS)
    a = n % len(BUT_BEGINNING)
    art, noun = BUT_ENDING[c]
    konj = BUT_BEGINNING[a]
    privation = DICKINSON_FLAT_LESS_LESS[b]
    # `doch` und `denn` sind reine Konjunktionen — sie stehen außerhalb
    # des Vorfelds, die Privation belegt dieses, V2 hält:
    #   `doch arglos ist die Erde`.
    # `dann` ist hingegen ein temporales Adverb, das selbst ins Vorfeld
    # will. Mit der parallelen Stellung `dann arglos ist die Erde` käme
    # das Verb auf Position 3, was V2 verletzt. Deshalb wird `dann` mit
    # umgekehrter Wortstellung gerendert:
    #   `dann ist die Erde arglos`.
    if konj == 'dann':
        return f'dann ist {art} {noun} {privation}'
    return f'{konj} {privation} ist {art} {noun}'


def _exclaim(n):
    b = n % len(TWO_SYLLABLE); n //= len(TWO_SYLLABLE)
    a = n % len(THREE_TO_FIVE_SYLLABLE)
    return THREE_TO_FIVE_SYLLABLE[a] + '! ' + TWO_SYLLABLE[b] + '!'


def _nailed(n):
    art, noun = NAILED_ENDING[n % len(NAILED_ENDING)]
    return 'genagelt an ' + art + ' ' + noun


def _second_line(n):
    m, r = divmod(n, 4)
    if r == 0:
        return _rise_and_go(m)
    if r == 1:
        return _but(m)
    if r == 2:
        return _exclaim(m)
    return _nailed(m)


# ── Strophenmontage ──────────────────────────────────────────────────

def _canonical(value: int) -> int:
    """Wickelt eine Koordinate auf den toroidalen Lattice [0, LATTICE_SIZE)."""
    v = value % LATTICE_SIZE
    return v if v >= 0 else v + LATTICE_SIZE


def _capitalise_first(line: str) -> str:
    """Großschreibung des ersten alphabetischen Zeichens. Idempotent
    bei bereits großgeschriebenen Wörtern; bewahrt die Einrückung am
    Zeilenanfang nicht (wird nur auf nicht-eingerückte Erstzeilen
    angewendet)."""
    for k, ch in enumerate(line):
        if ch.isalpha():
            return line[:k] + ch.upper() + line[k + 1:]
    return line


def generate_stanza(i: int, j: int) -> list[str]:
    """4-zeilige deutsche Strophe an Lattice-Koordinate (i, j).

    Spiegelt die `drawPair`-Logik von Sea and Spar Between: zwei Couplets
    aus (i, 2j) und (i, 2j+1). Output deterministisch — gleiche (i, j)
    liefert immer dieselben vier Zeilen.

    DE-Spezifika: Erste Zeile der Strophe (Index 0) wird mit
    Großschreibung erzwungen, damit deutsche Strophen typografisch
    einem Satzanfang entsprechen — *kreise weiter* → *Kreise weiter*,
    *je ein Mittag* → *Je ein Mittag*. Lattice-Indizes bleiben
    unverändert.
    """
    j2 = _canonical(j * 2)
    j2_next = _canonical(j2 + 1)
    return [
        _capitalise_first(_first_line(i + j2 + 1)),
        '  ' + _second_line(abs(i - j2) + 1),
        _first_line(i + j2_next + 1),
        '  ' + _second_line(abs(i - j2_next) + 1),
    ]


def generate_stanza_at(col: int, row: int) -> list[str]:
    """Deutsche Strophe an geographischer Gitterzelle (col, row)."""
    i, j = grid_to_lattice(col, row)
    return generate_stanza(i, j)
