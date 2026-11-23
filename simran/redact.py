"""Blind-screening redaction.

Strips things a matcher has no business looking at: name, email, phone, links,
and a few affiliation phrases that are known proxies for gender/ethnicity
(the Amazon "women's chess club" problem). Nothing here is perfect -- it's a
mitigation, and fairness.py measures how much it actually helps.
"""
from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{8,}\d)(?!\d)")
URL = re.compile(r"\b(?:https?://|www\.)\S+|\b(?:github|linkedin|gitlab)\.com/\S+", re.I)
PRONOUNS = re.compile(r"\b(he|she|him|her|his|hers|mr|mrs|ms|miss)\b\.?", re.I)
# affiliations that leak protected attributes. kept short on purpose; extend per deployment
AFFILIATION = re.compile(
    r"\b(women'?s?|female|male|men'?s|black|hispanic|latin[ao]x?|asian|muslim|christian|hindu|jewish|lgbtq?\+?)"
    r"(?=\s+(in|of|engineers|society|club|association|network|students|coders|who))", re.I)


def redact(text: str, names: list[str] | None = None) -> str:
    lines = text.splitlines()
    # first non-empty line of a resume is almost always the name (+ maybe a headline)
    for i, line in enumerate(lines):
        if line.strip():
            parts = re.split(r"\s[—–|-]\s", line, maxsplit=1)
            lines[i] = "[NAME]" + (" — " + parts[1] if len(parts) > 1 else "")
            break
    out = "\n".join(lines)
    for n in names or []:
        for piece in n.split():
            if len(piece) > 1:
                out = re.sub(rf"\b{re.escape(piece)}\b", "[NAME]", out)
    out = EMAIL.sub("[EMAIL]", out)
    out = URL.sub("[URL]", out)
    # date ranges like "2019 - 2021" also look like phone numbers, so count digits
    out = PHONE.sub(lambda m: "[PHONE]" if sum(c.isdigit() for c in m.group()) >= 10 else m.group(), out)
    out = PRONOUNS.sub("", out)
    out = AFFILIATION.sub("[GROUP]", out)
    return out
