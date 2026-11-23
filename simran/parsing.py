"""Turn raw resume / job description text into something we can score.

Nothing fancy here, just regexes that survived a lot of copy-pasted LinkedIn
postings. The rules are deliberately mirrored in web/js/engine.js, so if you
change one, change the other (tests/test_web_parity.py will complain).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date

from .taxonomy import Taxonomy, load_taxonomy

MONTHS = {m: i + 1 for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split())}

_DATE = r"(?:(?P<m{n}>jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(?P<y{n}>(?:19|20)\d{{2}})"
_RANGE = re.compile(
    _DATE.format(n=1) + r"\s*(?:-|–|—|to)\s*(?:" + _DATE.format(n=2) +
    r"|(?P<now>present|current|now|today))", re.I)
_YEARS_STATED = re.compile(r"(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:\w+\s+){0,3}?experience", re.I)
_YEARS_REQ = re.compile(
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*)?(?:years?|yrs?)", re.I)

# headings that switch a JD into "nice to have" mode
_PREF_HEAD = re.compile(r"^\s*(nice[ -]to[ -]have|preferred|bonus|pluses|a plus|good to have|desired)\b", re.I)
_REQ_HEAD = re.compile(r"^\s*(requirements?|required|must[ -]have|qualifications|what you.?ll need|you have|minimum)\b", re.I)
_ABOUT_HEAD = re.compile(r"^\s*(about (us|the company)|who we are|benefits|perks|our stack)\b", re.I)
_EXPERIENCE_HEAD = re.compile(r"^\s*(professional |work )?(experience|employment|work history)\s*:?\s*$", re.I)
_OTHER_HEAD = re.compile(r"^\s*(skills|technical skills|education|projects|certifications?|summary|profile|awards|publications|activities)\b.*:?\s*$", re.I)

SENIORITY = [  # (level, words) checked in this order
    (4, ("principal", "staff", "head of", "director", "architect")),
    (3, ("senior", "sr.", "sr ", "lead")),
    (1, ("junior", "jr.", "jr ", "intern", "graduate", "entry level", "entry-level", "associate")),
]

REMOTE = re.compile(r"\b(remote|work from home|wfh|distributed team|anywhere)\b", re.I)
OPEN_TO_REMOTE = re.compile(r"(open to|prefer|seeking|available for)\s+(remote|relocation|hybrid)", re.I)

TITLE_STOP = {"engineer", "developer", "the", "of", "and", "a", "an", "ii", "iii", "i", "sr", "jr",
              "senior", "junior", "lead", "staff", "principal", "intern", "-", "/", ","}


@dataclass
class ParsedResume:
    text: str
    skills: dict[str, list[int]]
    evidenced: set[str]          # skills that show up inside work experience bullets
    years: float
    titles: list[str]
    seniority: int
    location: str
    open_to_remote: bool


@dataclass
class ParsedJob:
    title: str
    text: str
    required: set[str]
    preferred: set[str]
    years_min: float | None
    seniority: int
    location: str
    remote: bool
    extra: dict = field(default_factory=dict)


def seniority_of(title: str) -> int:
    t = f" {title.lower()} "
    for level, words in SENIORITY:
        if any(w in t for w in words):
            return level
    return 2


def _experience_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges that belong to the work-experience section(s)."""
    spans, start, pos = [], None, 0
    for line in text.splitlines(keepends=True):
        if _EXPERIENCE_HEAD.match(line):
            start = pos + len(line)
        elif start is not None and _OTHER_HEAD.match(line):
            spans.append((start, pos))
            start = None
        pos += len(line)
    if start is not None:
        spans.append((start, pos))
    return spans


def _months(y: str, m: str | None) -> int:
    return int(y) * 12 + (MONTHS.get((m or "jan")[:3].lower(), 1) - 1)


def total_experience_years(text: str, today: date | None = None) -> float:
    """Sum of date ranges with overlaps merged. Falls back to "N years of experience"."""
    today = today or date.today()
    now = today.year * 12 + today.month - 1
    spans = []
    for m in _RANGE.finditer(text):
        a = _months(m["y1"], m["m1"])
        # end month is inclusive: "Jan 2019 - Feb 2022" is 38 months of work
        b = now if m["now"] else _months(m["y2"], m["m2"]) + 1
        if m["y2"] and not m["m2"]:
            b += 11  # "2019 - 2021" -> through Dec 2021
        if 0 <= b - a < 50 * 12:
            spans.append((a, b))
    spans.sort()
    total, cur = 0, None
    for a, b in spans:
        if cur and a <= cur[1]:
            cur = (cur[0], max(cur[1], b))
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = (a, b)
    if cur:
        total += cur[1] - cur[0]
    years = total / 12
    stated = [int(x) for x in _YEARS_STATED.findall(text)]
    if stated and years < 0.5:
        years = float(max(stated))
    return math.floor(years * 10 + 0.5) / 10   # not round(): keep it identical to the JS Math.round


def _resume_titles(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line[:1] in "-*•":
            continue  # bullets, not job titles
        if _RANGE.search(line) or re.search(r"\s[—–|-]\s", line[:80]):
            head = re.split(r"\s[—–|-]\s|\(|,", line)[0].strip()
            if 2 < len(head) < 60 and re.search(r"engineer|developer|scientist|analyst|manager|architect|designer|lead|intern|consultant|administrator|sre|devops", head, re.I):
                out.append(head)
    return out


def _location(text: str) -> str:
    m = re.search(r"location\s*:\s*([^\n|(]+)", text, re.I)
    return m.group(1).strip().lower() if m else ""


def parse_resume(text: str, tax: Taxonomy | None = None, today: date | None = None) -> ParsedResume:
    tax = tax or load_taxonomy()
    skills = tax.extract(text)
    spans = _experience_spans(text)
    evidenced = {s for s, offs in skills.items() if any(a <= o < b for o in offs for a, b in spans)}
    titles = _resume_titles(text)
    # seniority = most recent title (first one listed, resumes are reverse-chronological)
    sen = seniority_of(titles[0]) if titles else 2
    return ParsedResume(
        text=text,
        skills=skills,
        evidenced=evidenced,
        years=total_experience_years(text, today),
        titles=titles,
        seniority=sen,
        location=_location(text),
        open_to_remote=bool(OPEN_TO_REMOTE.search(text)) or bool(REMOTE.search(text[:300])),
    )


def parse_job(title: str, description: str, location: str = "", tax: Taxonomy | None = None) -> ParsedJob:
    tax = tax or load_taxonomy()
    required, preferred = set(), set()
    mode = "req"
    years = None
    for line in description.splitlines():
        if _PREF_HEAD.match(line):
            mode = "pref"
        elif _REQ_HEAD.match(line):
            mode = "req"
        elif _ABOUT_HEAD.match(line):
            mode = "skip"   # "our stack includes..." isn't a requirement
        if mode == "skip":
            continue
        found = set(tax.extract(line))
        if mode == "pref" or re.search(r"\b(nice to have|is a plus|a bonus|bonus points)\b", line, re.I):
            preferred |= found
        else:
            required |= found
        if mode == "req" and years is None and re.search(r"experience", line, re.I):
            m = _YEARS_REQ.search(line)
            if m:
                years = float(m.group(1))
    required |= set(tax.extract(title))
    preferred -= required
    loc = (location or "").lower()
    return ParsedJob(
        title=title,
        text=description,
        required=required,
        preferred=preferred,
        years_min=years,
        seniority=seniority_of(title),
        location=loc,
        remote=bool(REMOTE.search(loc)) or bool(REMOTE.search(description)),
    )


def title_tokens(title: str) -> set[str]:
    toks = re.findall(r"[a-z+#./]+", title.lower())
    return {t for t in toks if t not in TITLE_STOP and len(t) > 1}
