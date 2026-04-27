"""
Stanza generator — Python port of *Sea and Spar Between*.

======================================================================
  Conceptual anchor — the site of the appropriation
======================================================================

The word lists and line-generation functions below are a 1:1 port of
the JavaScript source of Nick Montfort and Stephanie Strickland's
*Sea and Spar Between* (2010, BSD licence). They must remain byte-for-
byte identical so that lattice coordinate (i, j) yields exactly the
same four-line stanza here and on the frontend, and so the
correspondence between a GPS hit and a deletable verse is well-
defined.

This is where *Remorseless Havoc* takes over their code and
turns it against itself. *Sea and Spar Between* produces an
apparently inexhaustible combinatorial ocean — over 225 trillion
stanzas on a toroidal lattice, generated on the fly, navigable
endlessly in the browser. The authors write that their work contains
as many verses as there are "fish in the sea." This project takes
that metaphor literally: it maps every cell of that lattice onto a
real square kilometre of ocean (see `grid.grid_to_lattice`), and then
lets the industrial fishing fleet do what it does — catch after
catch, hour after hour — until the poetic ocean is empty.

The procedure makes visible what pure combinatorics usually hides:
that algorithmic abundance, the vertigo of Borges' Library of Babel
or of Leibniz's combinatorial plenum, is bought at the cost of a
finite material substrate. On a real ocean floor, one trawl is one
trawl; in a database of stanzas, one delete is one delete. The
website enforces that equivalence.

See also: `Konzepttext Website.md`, `About this Document.md`.
======================================================================
"""

from .grid import LATTICE_SIZE, grid_to_lattice

# ── WORD LISTS (verbatim from the original JavaScript) ───────────────
# Source: Dickinson's poems, Melville's Moby-Dick. Do not edit.

SHORT_PHRASE = [
    'circle on', 'dash on', 'let them', 'listen now', 'loop on',
    'oh time', 'plunge on', 'reel on', 'roll on', 'run on', 'spool on',
    'steady', 'swerve me?', 'turn on', 'wheel on', 'whirl on', 'you -- too --',
    'fast-fish', 'loose-fish',
]

DICKINSON_NOUN = [
    ['air', 'art', 'care', 'door', 'dust', 'each', 'ear', 'earth', 'fair',
     'faith', 'fear', 'friend', 'gold', 'grace', 'grass', 'grave', 'hand',
     'hill', 'house', 'joy', 'keep', 'leg', 'might', 'mind', 'morn', 'name',
     'need', 'noon', 'pain', 'place', 'play', 'rest', 'rose', 'show',
     'sight', 'sky', 'snow', 'star', 'thought', 'tree', 'well', 'wind',
     'world', 'year'],
    ['again', 'alone', 'better', 'beyond', 'delight', 'dying', 'easy', 'enough',
     'ever', 'father', 'flower', 'further', 'himself', 'human', 'morning',
     'myself', 'power', 'purple', 'single', 'spirit', 'today'],
    ['another', 'paradise'],
    ['eternity'],
    ['immortality'],
]

COURSE_START = ['fix upon the ', 'cut to fit the ', 'how to withstand the ']

DICKINSON_SYLLABLE = [
    'bard', 'bead', 'bee', 'bin', 'blot', 'blur', 'buzz',
    'curl', 'dirt', 'disk', 'drum', 'fern', 'film', 'folk', 'germ', 'hive',
    'hood', 'husk', 'jay', 'pink', 'plot', 'spun', 'web',
]

MELVILLE_SYLLABLE = [
    'bag', 'buck', 'bunk', 'cane', 'chap', 'chop', 'dash',
    'dock', 'edge', 'fin', 'hag', 'hawk', 'hook', 'hoop', 'horn', 'howl',
    'iron', 'jack', 'jaw', 'kick', 'lime', 'loon', 'lurk', 'milk', 'pike',
    'rag', 'rail', 'ram', 'sack', 'salt', 'tool',
]

SYLLABLE = sorted(DICKINSON_SYLLABLE + MELVILLE_SYLLABLE)

DICKINSON_LESS_LESS = [
    ['art', 'base', 'blame', 'crumb', 'cure', 'date', 'death', 'drought',
     'fail', 'flesh', 'floor', 'foot', 'frame', 'fruit', 'goal', 'grasp',
     'guile', 'guilt', 'hue', 'key', 'league', 'list', 'need', 'note',
     'pang', 'pause', 'phrase', 'pier', 'plash', 'price', 'shame', 'shape',
     'sight', 'sound', 'star', 'stem', 'stint', 'stir', 'stop', 'swerve',
     'tale', 'taste', 'thread', 'worth'],
    ['arrest', 'blanket', 'concern', 'costume', 'cypher', 'degree', 'desire',
     'dower', 'efface', 'enchant', 'escape', 'fashion', 'flavor', 'honor',
     'kinsman', 'marrow', 'perceive', 'perturb', 'plummet', 'postpone',
     'recall', 'record', 'reduce', 'repeal', 'report', 'retrieve', 'tenant'],
    ['latitude', 'retriever'],
]

DICKINSON_FLAT_LESS_LESS = sorted(
    DICKINSON_LESS_LESS[0] + DICKINSON_LESS_LESS[1] + DICKINSON_LESS_LESS[2]
)

UP_VERB = ['bask', 'chime', 'dance', 'go', 'leave', 'move', 'rise', 'sing',
           'speak', 'step', 'turn', 'walk']

BUT_BEGINNING = ['but', 'for', 'then']
BUT_ENDING = ['earth', 'sea', 'sky', 'sun']

THREE_TO_FIVE_SYLLABLE = (
    DICKINSON_NOUN[2] + DICKINSON_NOUN[3] + DICKINSON_NOUN[4]
    + DICKINSON_LESS_LESS[2]
)
TWO_SYLLABLE = DICKINSON_NOUN[1] + DICKINSON_LESS_LESS[1]

NAILED_ENDING = ['coffin', 'deck', 'desk', 'groove', 'mast', 'spar', 'pole',
                 'plank', 'rail', 'room', 'sash']


# ── Line generators (one branch per verse-type in the original) ──────

def _short(n):
    return SHORT_PHRASE[n % len(SHORT_PHRASE)]


def _one_noun(n):
    L = len(DICKINSON_NOUN[0])
    d = n % L; n //= L
    c = n % L; n //= L
    b = n % L; n //= L
    a = n % L
    dn = DICKINSON_NOUN[0]
    return f'one {dn[a]} one {dn[b]} one {dn[c]} one {dn[d]}'


def _compound_course(n):
    c = n % len(SYLLABLE); n //= len(SYLLABLE)
    b = n % len(SYLLABLE); n //= len(SYLLABLE)
    a = n % len(COURSE_START)
    return COURSE_START[a] + SYLLABLE[b] + SYLLABLE[c] + ' course'


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
    dash = ' --' if DICKINSON_FLAT_LESS_LESS[a] in DICKINSON_LESS_LESS[0] else ''
    return DICKINSON_FLAT_LESS_LESS[a] + 'less ' + UP_VERB[b] + ' and ' + UP_VERB[c] + dash


def _but(n):
    c = n % len(BUT_ENDING); n //= len(BUT_ENDING)
    b = n % len(DICKINSON_FLAT_LESS_LESS); n //= len(DICKINSON_FLAT_LESS_LESS)
    a = n % len(BUT_BEGINNING)
    return BUT_BEGINNING[a] + ' ' + DICKINSON_FLAT_LESS_LESS[b] + 'less is the ' + BUT_ENDING[c]


def _exclaim(n):
    b = n % len(TWO_SYLLABLE); n //= len(TWO_SYLLABLE)
    a = n % len(THREE_TO_FIVE_SYLLABLE)
    return THREE_TO_FIVE_SYLLABLE[a] + '! ' + TWO_SYLLABLE[b] + '!'


def _nailed(n):
    return 'nailed to the ' + NAILED_ENDING[n % len(NAILED_ENDING)]


def _second_line(n):
    m, r = divmod(n, 4)
    if r == 0:
        return _rise_and_go(m)
    if r == 1:
        return _but(m)
    if r == 2:
        return _exclaim(m)
    return _nailed(m)


# ── Stanza assembly ──────────────────────────────────────────────────

def _canonical(value: int) -> int:
    """Wrap a coordinate into the toroidal lattice [0, LATTICE_SIZE)."""
    v = value % LATTICE_SIZE
    return v if v >= 0 else v + LATTICE_SIZE


def generate_stanza(i: int, j: int) -> list[str]:
    """
    Produce the 4-line stanza at lattice coordinates (i, j).

    Mirrors the `drawPair` logic of the original JavaScript: two
    couplets built from (i, 2j) and (i, 2j+1). The output is
    deterministic — the same (i, j) always returns the same four
    lines — which is what makes it sensible to think of a cell as a
    verse that can be "deleted."
    """
    j2 = _canonical(j * 2)
    j2_next = _canonical(j2 + 1)
    return [
        _first_line(i + j2 + 1),
        '  ' + _second_line(abs(i - j2) + 1),
        _first_line(i + j2_next + 1),
        '  ' + _second_line(abs(i - j2_next) + 1),
    ]


def generate_stanza_at(col: int, row: int) -> list[str]:
    """Stanza at geographic grid cell (col, row)."""
    i, j = grid_to_lattice(col, row)
    return generate_stanza(i, j)
