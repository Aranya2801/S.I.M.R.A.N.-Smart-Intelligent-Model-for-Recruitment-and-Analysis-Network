"""Pairwise (resume, job) features.

CORE features are the ones the browser engine can also compute without a corpus;
TEXT features need a fitted TF-IDF / BM25 index, so they only exist on the python side.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

from .parsing import ParsedJob, ParsedResume, title_tokens
from .taxonomy import Taxonomy, load_taxonomy

CORE = [
    "req_cov",        # idf-weighted coverage of required skills (with evidence + related credit)
    "pref_cov",       # same for nice-to-haves
    "req_evid",       # coverage counting only skills backed by an experience bullet
    "exp_short",      # years below the stated minimum
    "exp_over",       # way above the minimum (overqualified)
    "sen_under",      # job is more senior than the candidate's last title
    "sen_over",
    "title_sim",
    "domain_sim",     # cosine between skill-category histograms
    "loc_ok",
]
TEXT = ["tfidf_cos", "bm25"]
ALL = CORE + TEXT

# credit given to a required skill depending on how the resume shows it
CREDIT_EVIDENCED = 1.0   # used in an experience bullet
CREDIT_LISTED = 1.0      # only in a skills list. 0.8 hurt on SIMRAN-Synth, see REPORT.md sec 5.3
CREDIT_RELATED = 0.5     # candidate has a close sibling (mysql for postgres, gcp for aws)


def skill_credit(skill: str, res: ParsedResume, tax: Taxonomy) -> tuple[float, str]:
    if skill in res.skills:
        if skill in res.evidenced:
            return CREDIT_EVIDENCED, "evidenced"
        return CREDIT_LISTED, "listed"
    for other in sorted(tax.related.get(skill, ())):
        if other in res.skills:
            return CREDIT_RELATED, f"related:{other}"
    return 0.0, "missing"


def weighted_coverage(skills, res, tax, idf, evidenced_only=False) -> float:
    if not skills:
        return 0.5   # nothing asked -> neutral, not perfect
    num = den = 0.0
    for s in skills:
        w = idf.get(s, 1.0)
        if evidenced_only:
            num += w * (s in res.evidenced)
        else:
            num += w * skill_credit(s, res, tax)[0]
        den += w
    return num / den


def missing_required(res, job, tax=None) -> list[str]:
    tax = tax or load_taxonomy()
    return sorted(s for s in job.required if skill_credit(s, res, tax)[0] == 0)


def _cat_hist(skills, tax) -> Counter:
    return Counter(tax.category(s) for s in skills)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


def _city(loc: str) -> str:
    return loc.split(",")[0].strip()


def location_ok(res: ParsedResume, job: ParsedJob) -> float:
    if job.remote:
        return 1.0 if res.open_to_remote or not res.location else 0.7
    if not job.location or not res.location:
        return 0.5
    return 1.0 if _city(job.location) == _city(res.location) else 0.0


def core_features(res: ParsedResume, job: ParsedJob, idf: dict | None = None,
                  tax: Taxonomy | None = None) -> np.ndarray:
    tax = tax or load_taxonomy()
    idf = idf or {}
    ymin = job.years_min
    short = max(0.0, ymin - res.years) if ymin is not None else 0.0
    over = max(0.0, res.years - ymin - 5) if ymin is not None else 0.0
    rt = set()
    for t in res.titles[:2]:
        rt |= title_tokens(t)
    jt = title_tokens(job.title)
    title_sim = len(rt & jt) / len(rt | jt) if rt and jt else 0.0
    dom = _cosine(_cat_hist(job.required | job.preferred, tax), _cat_hist(res.skills, tax))
    return np.array([
        weighted_coverage(job.required, res, tax, idf),
        weighted_coverage(job.preferred, res, tax, idf),
        weighted_coverage(job.required, res, tax, idf, evidenced_only=True),
        min(short, 5) / 5,
        min(over, 10) / 10,
        max(0, job.seniority - res.seniority) / 3,
        max(0, res.seniority - job.seniority) / 3,
        title_sim,
        dom,
        location_ok(res, job),
    ], dtype=float)


def skill_idf(jobs: list[ParsedJob]) -> dict[str, float]:
    """Rarer skills across the job pool count more (kubernetes > git)."""
    n = len(jobs)
    df = Counter(s for j in jobs for s in (j.required | j.preferred))
    return {s: math.log((n + 1) / (c + 1)) + 1 for s, c in df.items()}
