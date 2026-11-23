"""Ranking metrics + grouped cross-validation.

Each candidate is a "query" and the jobs in their slate are the documents, so
this is the job-recommendation view of the problem (rank jobs for a person).
"""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import GroupKFold


def dcg(rels, k):
    rels = np.asarray(rels, dtype=float)[:k]
    return float(np.sum((2 ** rels - 1) / np.log2(np.arange(2, len(rels) + 2))))


def ndcg_at_k(scores, labels, k=10):
    order = np.argsort(-np.asarray(scores), kind="stable")
    ideal = dcg(sorted(labels, reverse=True), k)
    return dcg(np.asarray(labels)[order], k) / ideal if ideal > 0 else np.nan


def average_precision(scores, labels, rel=2):
    order = np.argsort(-np.asarray(scores), kind="stable")
    hits = (np.asarray(labels)[order] >= rel).astype(float)
    if hits.sum() == 0:
        return np.nan
    prec = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float((prec * hits).sum() / hits.sum())


def reciprocal_rank(scores, labels, rel=2):
    order = np.argsort(-np.asarray(scores), kind="stable")
    hits = np.where(np.asarray(labels)[order] >= rel)[0]
    return 1.0 / (hits[0] + 1) if len(hits) else np.nan


def precision_at_k(scores, labels, k=5, rel=2):
    order = np.argsort(-np.asarray(scores), kind="stable")[:k]
    return float((np.asarray(labels)[order] >= rel).mean())


METRICS = {
    "nDCG@5": lambda s, l: ndcg_at_k(s, l, 5),
    "nDCG@10": lambda s, l: ndcg_at_k(s, l, 10),
    "MAP": average_precision,
    "MRR": reciprocal_rank,
    "P@5": precision_at_k,
}


def per_query(scores_list, labels_list) -> dict[str, np.ndarray]:
    return {m: np.array([f(s, l) for s, l in zip(scores_list, labels_list)]) for m, f in METRICS.items()}


def cross_validate(make_ranker, resumes, jobs, labels, n_splits=5):
    """Returns per-query metric arrays (aligned with the input order) using
    out-of-fold scores, so every query is scored by a model that never saw it."""
    n = len(resumes)
    oof = [None] * n
    gkf = GroupKFold(n_splits=n_splits)
    for tr, te in gkf.split(np.zeros(n), groups=np.arange(n)):
        r = make_ranker().fit([resumes[i] for i in tr], [jobs[i] for i in tr], [labels[i] for i in tr])
        for i in te:
            oof[i] = r.score(resumes[i], jobs[i])
    return per_query(oof, labels), oof


def bootstrap_ci(x, n=2000, seed=0, alpha=0.05):
    x = x[~np.isnan(x)]
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n, len(x)), replace=True).mean(1)
    return float(x.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def paired_bootstrap_p(a, b, n=5000, seed=0):
    """One-sided p-value for mean(a) > mean(b) on the same queries."""
    mask = ~(np.isnan(a) | np.isnan(b))
    d = a[mask] - b[mask]
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n, len(d)), replace=True).mean(1)
    return float((boots <= 0).mean())
