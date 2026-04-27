"""
Shannon entropy of a stanza — an observation, not a property.

The ocean itself knows no entropy ordering. Entropy is measured
*after* the stanzas have been pulled from the water and is used only
at display time: the per-vessel poems are sorted from high entropy
(diverse vocabulary, a living ecosystem of language) down to low
entropy (monotony, collapse, exhaustion). Storage stays chronological.
"""

import math
from collections import Counter


def stanza_entropy(stanza_lines: list[str]) -> float:
    words = " ".join(stanza_lines).lower().split()
    if not words:
        return 0.0
    counts = Counter(words)
    total = len(words)
    H = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            H -= p * math.log2(p)
    return round(H, 4)
