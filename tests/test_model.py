from datetime import date

import numpy as np

from simran.datasets.synthetic import TODAY, build_benchmark
from simran.evaluate import cross_validate
from simran.model import CoreModel
from simran.parsing import parse_job, parse_resume
from simran.rankers import FeatureRanker, RuleRanker


def _small():
    b = build_benchmark(n_candidates=60, n_jobs=400, seed=5)
    pj = [parse_job(j.title, j.text, j.location) for j in b.jobs]
    res = [parse_resume(c.text, today=TODAY) for c in b.candidates]
    jobs = [[pj[i] for i in s] for s in b.slates]
    return res, jobs, [np.array(l) for l in b.labels]


def test_generator_is_deterministic():
    a = build_benchmark(5, 400, seed=1)
    b = build_benchmark(5, 400, seed=1)
    assert a.candidates[0].text == b.candidates[0].text and a.labels == b.labels


def test_learned_ranker_beats_rubric_on_small_run():
    res, jobs, labels = _small()
    v3, _ = cross_validate(lambda: FeatureRanker("core", "logreg"), res, jobs, labels, n_splits=3)
    rub, _ = cross_validate(lambda: RuleRanker(), res, jobs, labels, n_splits=3)
    assert np.nanmean(v3["nDCG@10"]) > np.nanmean(rub["nDCG@10"])


def test_shipped_model_scores_sensibly():
    m = CoreModel.load()
    r = parse_resume("X — Backend Engineer\nLocation: Austin, TX\nEXPERIENCE\n"
                     "Backend Engineer — Co (Jan 2019 – Present)\n- Python, PostgreSQL and Docker services on AWS\n",
                     today=date(2025, 1, 1))
    good = parse_job("Backend Engineer", "Requirements\n- 3+ years experience\n- Python, PostgreSQL, Docker", "Austin, TX")
    bad = parse_job("iOS Developer", "Requirements\n- 5+ years experience\n- Swift, iOS, Kotlin", "Berlin, Germany")
    assert m.score(r, good) > 70 > 30 > m.score(r, bad)


def test_generator_ignores_hash_seed():
    # sets iterate in PYTHONHASHSEED order; the generator must not depend on that
    import os
    import subprocess
    import sys
    code = ("import hashlib,json;from simran.datasets.synthetic import build_benchmark;"
            "b=build_benchmark(20,400,seed=3);"
            "print(hashlib.md5(json.dumps([c.text for c in b.candidates]+[b.labels]).encode()).hexdigest())")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outs = {subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": h}).stdout for h in ("1", "2")}
    assert len(outs) == 1
