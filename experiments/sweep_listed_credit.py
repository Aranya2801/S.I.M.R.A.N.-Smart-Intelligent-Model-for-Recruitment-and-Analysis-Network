"""Sweep for REPORT.md sec 5.3: does discounting skills that only appear in the
skills list (no experience bullet) help against keyword stuffing? (It doesn't.)"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_benchmark import prepare  # noqa: E402
from simran import features as F  # noqa: E402
from simran.datasets.synthetic import build_benchmark  # noqa: E402
from simran.evaluate import cross_validate  # noqa: E402
from simran.rankers import FeatureRanker  # noqa: E402

bench = build_benchmark(300, seed=21, stuff_rate=0.3)
res, jobs, labels = prepare(bench)
stuffed = np.array([c.stuffer for c in bench.candidates])
default = F.CREDIT_LISTED
print("listed_credit  nDCG@10  stuffed  honest")
for credit in [1.0, 0.8, 0.6, 0.4]:
    F.CREDIT_LISTED = credit
    pq, _ = cross_validate(lambda: FeatureRanker("core", "logreg"), res, jobs, labels)
    nd = pq["nDCG@10"]
    print(f"{credit:>13}  {np.nanmean(nd):.4f}   {np.nanmean(nd[stuffed]):.4f}   {np.nanmean(nd[~stuffed]):.4f}")
F.CREDIT_LISTED = default
