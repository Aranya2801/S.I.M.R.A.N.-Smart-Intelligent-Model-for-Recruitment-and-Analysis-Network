"""Counterfactual fairness checks.

Idea: take a resume, change *only* the name (and the email derived from it),
or swap a neutral club for one that signals a protected group, and see whether
the scores move. An attribute-blind matcher should give identical scores.

We report the mean absolute score change and how often the top-5 changes.
"""
from __future__ import annotations

import re

import numpy as np

from .datasets.synthetic import CLUB_PAIRS, NAME_GROUPS
from .parsing import parse_resume
from .redact import redact


def swap_name(text: str, old: str, new: str) -> str:
    out = text.replace(old, new)
    return out.replace(old.lower().replace(" ", "."), new.lower().replace(" ", "."))


def swap_club(text: str) -> str:
    """Neutral club -> the same club with a group marker in front."""
    for neutral, proxy in CLUB_PAIRS:
        if f"Member, {neutral}" in text:
            return text.replace(f"Member, {neutral}", f"Member, {proxy}")
    return text


def _top5(s):
    return set(np.argsort(-s)[:5])


def counterfactual_test(ranker, bench, idx, today, blind=False, kind="name", seed=0):
    """Returns dict with mean |Δscore| (in the ranker's units, normalised by the
    score range on the slate) and share of candidates whose top-5 changed."""
    rng = np.random.default_rng(seed)
    deltas, flips = [], 0
    groups = list(NAME_GROUPS)
    for i in idx:
        c = bench.candidates[i]
        jobs = bench.jobs_parsed[i]
        base_text = c.text
        if kind == "name":
            g = rng.choice([x for x in groups if x != c.name_group])
            first, last = NAME_GROUPS[g]
            alt_text = swap_name(base_text, c.name, f"{rng.choice(first)} {rng.choice(last)}")
        else:
            alt_text = swap_club(base_text)
        if blind:
            base_text, alt_text = redact(base_text), redact(alt_text)
        s0 = ranker.score(parse_resume(base_text, today=today), jobs)
        s1 = ranker.score(parse_resume(alt_text, today=today), jobs)
        rngw = (s0.max() - s0.min()) or 1.0
        deltas.append(np.abs(s1 - s0).mean() / rngw)
        flips += _top5(s0) != _top5(s1)
    return {"mean_abs_delta": float(np.mean(deltas)), "top5_changed": flips / len(idx)}
