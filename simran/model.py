"""Load the exported core model (models/simran_v3_core.json) and score with it.

This is the exact computation web/js/engine.js does in the browser, so it
doubles as the reference implementation for the parity test.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import features as F
from .parsing import ParsedJob, ParsedResume
from .taxonomy import load_taxonomy

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "simran_v3_core.json"

# plain-English text for the explanation panel: (said when it helps, said when it hurts)
READABLE = {
    "req_cov": ("covers most required skills", "missing several required skills"),
    "pref_cov": ("has the nice-to-haves", "few of the nice-to-haves"),
    "req_evid": ("required skills show up in real work", "required skills only in the skills list"),
    "exp_short": ("meets the experience ask", "short on years of experience"),
    "exp_over": ("experience level fits", "much more experienced than asked"),
    "sen_under": ("seniority fits", "role is more senior than current title"),
    "sen_over": ("seniority fits", "role is more junior than current title"),
    "title_sim": ("past titles look like this role", "past titles differ from this role"),
    "domain_sim": ("skill profile fits the domain", "skill profile is from a different domain"),
    "loc_ok": ("location / remote works", "location doesn't line up"),
}


def phrase(feature: str, contribution: float) -> str:
    good, bad = READABLE.get(feature, (feature, feature))
    return good if contribution > 0 else bad


def level(score: float) -> str:
    return "High" if score >= 80 else "Medium" if score >= 50 else "Low"


@dataclass
class Match:
    job: ParsedJob
    score: float                  # 0-100, calibrated probability of a good (label>=2) match
    level: str
    missing: list[str]
    matched: list[tuple[str, str]]  # (skill, how: evidenced/listed/related:x)
    reasons: list[tuple[str, float]]


class CoreModel:
    def __init__(self, spec: dict):
        self.spec = spec
        self.names = spec["features"]
        self.coef = np.array(spec["coef"])
        self.mean = np.array(spec["mean"])
        self.scale = np.array(spec["scale"])
        self.b = spec["intercept"]
        self.idf = spec["idf"]
        self.tax = load_taxonomy()

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL) -> "CoreModel":
        return cls(json.loads(Path(path).read_text()))

    def _x(self, res: ParsedResume, job: ParsedJob) -> np.ndarray:
        full = F.core_features(res, job, self.idf, self.tax)
        return np.array([full[F.CORE.index(n)] for n in self.names])

    def score(self, res: ParsedResume, job: ParsedJob) -> float:
        z = (self._x(res, job) - self.mean) / self.scale
        logit = float(z @ self.coef + self.b)
        return 100.0 / (1.0 + math.exp(-logit))

    def match(self, res: ParsedResume, jobs: list[ParsedJob]) -> list[Match]:
        out = []
        for j in jobs:
            x = self._x(res, j)
            z = (x - self.mean) / self.scale
            contrib = z * self.coef
            s = 100.0 / (1.0 + math.exp(-float(contrib.sum() + self.b)))
            reasons = sorted(((phrase(n, float(c)), float(c)) for n, c in zip(self.names, contrib)),
                             key=lambda r: -abs(r[1]))
            matched = []
            for sk in sorted(j.required | j.preferred):
                cr, how = F.skill_credit(sk, res, self.tax)
                if cr > 0:
                    matched.append((sk, how))
            out.append(Match(j, s, level(s), F.missing_required(res, j, self.tax), matched, reasons[:4]))
        return sorted(out, key=lambda m: -m.score)
