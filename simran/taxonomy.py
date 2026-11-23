"""Skill taxonomy + extraction.

The taxonomy lives in data/skills.json so the browser version (web/js/taxonomy.js)
can be generated from the same file -- see scripts/export_web_assets.py.

Extraction is dictionary based on purpose. I tried a spaCy NER model early on
and it was worse on short skill lists ("Python, SQL, R") and much slower, and the
whole point of this project is that every score can be traced back to a phrase
in the resume.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "skills.json"

# phrases like "no experience with X" / "not familiar with X" shouldn't count
_NEGATION = re.compile(
    r"\b(no|not|never|without|lack(?:ing)?|unfamiliar)\b[^.;\n]{0,35}$", re.I
)
_LIST_LINE = re.compile(r"^\s*[\w /&-]{2,30}:\s*\S|[,|•·].*[,|•·]")
_SENTENCE_START = re.compile(r"(^|[.!?]\s+|\n\s*[-*•]?\s*)$")


@dataclass
class Taxonomy:
    skills: dict[str, dict]
    related: dict[str, set[str]] = field(default_factory=dict)
    ambiguous: set[str] = field(default_factory=set)

    def __post_init__(self):
        # alias -> canonical. longest first so "react native" wins over "react"
        pairs = []
        for canon, meta in self.skills.items():
            pairs.append((canon, canon))
            pairs.extend((a.lower(), canon) for a in meta.get("aliases", []))
        pairs.sort(key=lambda p: -len(p[0]))
        self.alias_to_canon = dict(pairs)
        self._patterns = [(alias, canon, _compile(alias)) for alias, canon in pairs]

    def category(self, skill: str) -> str:
        return self.skills.get(skill, {}).get("category", "other")

    def is_related(self, a: str, b: str) -> bool:
        return b in self.related.get(a, ())

    def extract(self, text: str) -> dict[str, list[int]]:
        """Return {canonical_skill: [char offsets of each mention]}."""
        found: dict[str, list[int]] = {}
        taken: list[tuple[int, int]] = []  # spans already claimed by a longer alias
        low = text.lower()
        for alias, canon, pat in self._patterns:
            for m in pat.finditer(low):
                s, e = m.span()
                if any(s < te and e > ts for ts, te in taken):
                    continue
                if _NEGATION.search(low[max(0, s - 40):s]):
                    continue
                if alias in self.ambiguous and not _ambiguous_ok(text, s, e):
                    continue
                taken.append((s, e))
                found.setdefault(canon, []).append(s)
        return found


def _compile(alias: str) -> re.Pattern:
    # \b doesn't work around "c++", ".net", "c#" so build explicit boundaries
    return re.compile(r"(?<![\w+#.])" + re.escape(alias) + r"(?![\w+#]|\.\w)")


def _ambiguous_ok(text: str, s: int, e: int) -> bool:
    """Short / common-word aliases (go, r, rest, swift...) only count in a skills
    list or when written capitalised mid-sentence."""
    line_start = text.rfind("\n", 0, s) + 1
    line_end = text.find("\n", e)
    line = text[line_start: line_end if line_end != -1 else len(text)]
    if _LIST_LINE.search(line):
        return True
    word = text[s:e]
    if word[:1].isupper() and not _SENTENCE_START.search(text[max(0, s - 4):s]):
        return True
    return False


@lru_cache(maxsize=1)
def load_taxonomy(path: str | None = None) -> Taxonomy:
    raw = json.loads(Path(path or DATA_PATH).read_text())
    related: dict[str, set[str]] = {}
    for group in raw.get("related", []):
        for a in group:
            related.setdefault(a, set()).update(x for x in group if x != a)
    return Taxonomy(raw["skills"], related, set(raw.get("ambiguous", [])))
