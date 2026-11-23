"""All the rankers compared in the benchmark.

Every ranker exposes the same two methods:
    fit(resumes, jobs_per_resume, labels_per_resume)   (no-op for unsupervised ones)
    score(resume, jobs) -> np.ndarray                   (higher = better match)

`resumes` are ParsedResume, `jobs` are ParsedJob. Keeping the parsed objects
around (instead of a big feature matrix) makes it easy to plug in rankers that
want raw text.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import features as F
from .parsing import ParsedJob, ParsedResume
from .taxonomy import load_taxonomy
from .text import BM25, TfidfIndex


def _job_doc(j: ParsedJob) -> str:
    return f"{j.title}\n{j.text}"


class Ranker:
    name = "base"

    def fit(self, resumes, jobs, labels):
        return self

    def score(self, res: ParsedResume, jobs: list[ParsedJob]) -> np.ndarray:
        raise NotImplementedError


class TfidfRanker(Ranker):
    name = "TF-IDF cosine"

    def fit(self, resumes, jobs, labels):
        docs = [r.text for r in resumes] + [_job_doc(j) for js in jobs for j in js]
        self.idx = TfidfIndex().fit(docs)
        return self

    def score(self, res, jobs):
        return self.idx.cosine(res.text, [_job_doc(j) for j in jobs])


class BM25Ranker(Ranker):
    name = "BM25"

    def fit(self, resumes, jobs, labels):
        uniq = {id(j): j for js in jobs for j in js}
        self.bm = BM25().fit([_job_doc(j) for j in uniq.values()])
        return self

    def score(self, res, jobs):
        return self.bm.score(res.text, [_job_doc(j) for j in jobs])


class SkillJaccardRanker(Ranker):
    name = "Skill Jaccard"

    def score(self, res, jobs):
        r = set(res.skills)
        out = []
        for j in jobs:
            js = j.required | j.preferred
            out.append(len(r & js) / len(r | js) if (r | js) else 0.0)
        return np.array(out)


class RuleRanker(Ranker):
    """The 40/30/20/10 rubric from SIMRAN v2's prompt, but computed instead of
    asked for. Plain (unweighted) skill overlap, no evidence or related credit."""
    name = "v2 rubric (40/30/20/10)"

    def score(self, res, jobs):
        tax = load_taxonomy()
        out = []
        for j in jobs:
            req = j.required or j.preferred
            skills = len(req & set(res.skills)) / len(req) if req else 0.5
            if j.years_min:
                exp = 1 - min(1.0, max(0.0, j.years_min - res.years) / j.years_min)
            else:
                exp = 1.0
            x = F.core_features(res, j, tax=tax)
            role = x[F.CORE.index("title_sim")]
            loc = F.location_ok(res, j)
            out.append(100 * (0.4 * skills + 0.3 * exp + 0.2 * role + 0.1 * loc))
        return np.array(out)


class FeatureRanker(Ranker):
    """Learned ranker over the hand-built features (the "SIMRAN v3" model)."""

    def __init__(self, feature_set: str = "all", model: str = "logreg", drop: tuple[str, ...] = (),
                 relevant_at: int = 2, C: float = 1.0):
        names = F.ALL if feature_set == "all" else F.CORE
        self.names = [n for n in names if n not in drop]
        self.model_kind = model
        self.relevant_at = relevant_at
        self.C = C
        self.name = {"logreg": "SIMRAN v3 (logreg)", "gbdt": "SIMRAN v3 (GBDT)"}[model]
        if feature_set == "core":
            self.name += " core"
        if drop:
            self.name += " −" + ",".join(drop)
        self.tax = load_taxonomy()

    # -- feature plumbing -------------------------------------------------
    def _matrix(self, res, jobs):
        core = np.stack([F.core_features(res, j, self.idf, self.tax) for j in jobs])
        cols = {n: core[:, i] for i, n in enumerate(F.CORE)}
        if any(n in self.names for n in F.TEXT):
            docs = [_job_doc(j) for j in jobs]
            cols["tfidf_cos"] = self.tfidf.cosine(res.text, docs)
            bm = self.bm25.score(res.text, docs)
            cols["bm25"] = bm / bm.max() if bm.max() > 0 else bm   # per-query max norm
        return np.column_stack([cols[n] for n in self.names])

    def fit(self, resumes, jobs, labels):
        uniq = list({id(j): j for js in jobs for j in js}.values())
        self.idf = F.skill_idf(uniq)
        if any(n in self.names for n in F.TEXT):
            self.tfidf = TfidfIndex().fit([r.text for r in resumes] + [_job_doc(j) for j in uniq])
            self.bm25 = BM25().fit([_job_doc(j) for j in uniq])
        X = np.vstack([self._matrix(r, js) for r, js in zip(resumes, jobs)])
        y = (np.concatenate(labels) >= self.relevant_at).astype(int)
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)
        if self.model_kind == "logreg":
            self.clf = LogisticRegression(C=self.C, max_iter=2000)  # unweighted, so predict_proba stays calibrated
        else:
            self.clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08,
                                                      max_leaf_nodes=15, l2_regularization=1.0,
                                                      random_state=0)
        self.clf.fit(Xs, y)
        return self

    def score(self, res, jobs):
        return self.clf.predict_proba(self.scaler.transform(self._matrix(res, jobs)))[:, 1]

    # -- explanations (linear model only) ---------------------------------
    def explain(self, res, job) -> list[tuple[str, float, float]]:
        """(feature, raw value, contribution to the logit) sorted by |contribution|.
        Contribution is w_i * standardised(x_i), so it's relative to an average pair."""
        assert self.model_kind == "logreg", "explanations need the linear model"
        x = self._matrix(res, [job])[0]
        z = self.scaler.transform(x[None])[0]
        contrib = self.clf.coef_[0] * z
        rows = list(zip(self.names, x, contrib))
        return sorted(rows, key=lambda r: -abs(r[2]))

    def weights(self) -> dict[str, float]:
        return dict(zip(self.names, self.clf.coef_[0]))


def baseline_suite():
    return [TfidfRanker(), BM25Ranker(), SkillJaccardRanker(), RuleRanker()]
