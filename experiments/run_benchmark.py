"""Reproduces every number in docs/REPORT.md.

    python experiments/run_benchmark.py            # full run, ~3-4 min on a laptop
    python experiments/run_benchmark.py --quick    # 150 candidates, for sanity checks

Writes results/benchmark.json, results/tables.md and models/simran_v3_core.json
(the weights the browser engine uses).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simran import features as F                       # noqa: E402
from simran.datasets.synthetic import TODAY, build_benchmark  # noqa: E402
from simran.evaluate import bootstrap_ci, cross_validate, paired_bootstrap_p  # noqa: E402
from simran.fairness import counterfactual_test       # noqa: E402
from simran.parsing import parse_job, parse_resume    # noqa: E402
from simran.rankers import FeatureRanker, baseline_suite  # noqa: E402

GROUPS = {
    "skills": ("req_cov", "pref_cov", "req_evid"),
    "experience": ("exp_short", "exp_over"),
    "seniority": ("sen_under", "sen_over"),
    "title": ("title_sim",),
    "domain": ("domain_sim",),
    "location": ("loc_ok",),
    "text (tf-idf+bm25)": ("tfidf_cos", "bm25"),
}


def prepare(bench):
    pj = [parse_job(j.title, j.text, j.location) for j in bench.jobs]
    resumes = [parse_resume(c.text, today=TODAY) for c in bench.candidates]
    jobs = [[pj[i] for i in s] for s in bench.slates]
    labels = [np.array(l) for l in bench.labels]
    bench.jobs_parsed = jobs
    return resumes, jobs, labels


def summarise(per_q):
    return {m: bootstrap_ci(v) for m, v in per_q.items()}


def fmt_row(name, summ, metrics=("nDCG@5", "nDCG@10", "MAP", "MRR", "P@5")):
    cells = [f"{summ[m][0]:.3f} ({summ[m][1]:.3f}–{summ[m][2]:.3f})" for m in metrics]
    return f"| {name} | " + " | ".join(cells) + " |"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    n = 150 if args.quick else 600
    t0 = time.time()
    out = {"config": {"n_candidates": n, "n_jobs": 900, "slate": 30, "seed": args.seed, "folds": 5}}
    md = []

    bench = build_benchmark(n_candidates=n, seed=args.seed)
    resumes, jobs, labels = prepare(bench)
    lab = np.concatenate(labels)
    out["label_distribution"] = {int(k): int((lab == k).sum()) for k in range(4)}
    print(f"built benchmark: {n} candidates x 30 jobs, labels {out['label_distribution']}")

    # ---- 1. main comparison -------------------------------------------------
    factories = [(r.name, (lambda r=r: type(r)())) for r in baseline_suite()]
    factories += [
        ("SIMRAN v3 (logreg)", lambda: FeatureRanker("all", "logreg")),
        ("SIMRAN v3 (logreg) core", lambda: FeatureRanker("core", "logreg")),
        ("SIMRAN v3 (GBDT)", lambda: FeatureRanker("all", "gbdt")),
    ]
    perq, main = {}, {}
    for name, fac in factories:
        pq, _ = cross_validate(fac, resumes, jobs, labels)
        perq[name] = pq
        main[name] = summarise(pq)
        print(f"  {name:28s} nDCG@10={main[name]['nDCG@10'][0]:.3f}  MAP={main[name]['MAP'][0]:.3f}")
    out["main"] = main

    md += ["## Main results (5-fold grouped CV, mean and 95% bootstrap CI)", "",
           "| Method | nDCG@5 | nDCG@10 | MAP | MRR | P@5 |", "|---|---|---|---|---|---|"]
    md += [fmt_row(k, v) for k, v in main.items()]

    base_names = [r.name for r in baseline_suite()]
    best_base = max(base_names, key=lambda k: main[k]["nDCG@10"][0])
    sig = {}
    for v3 in ["SIMRAN v3 (logreg)", "SIMRAN v3 (GBDT)"]:
        sig[v3] = {m: paired_bootstrap_p(perq[v3][m], perq[best_base][m]) for m in ("nDCG@10", "MAP")}
    out["significance_vs_best_baseline"] = {"baseline": best_base, "p_values": sig}
    md += ["", f"Best baseline: **{best_base}**. Paired bootstrap p-values (one-sided, v3 > baseline): "
           + "; ".join(f"{k}: nDCG@10 p={v['nDCG@10']:.4f}, MAP p={v['MAP']:.4f}" for k, v in sig.items())]

    # ---- 2. ablations -------------------------------------------------------
    full = main["SIMRAN v3 (logreg)"]["nDCG@10"][0]
    abl = {}
    for g, cols in GROUPS.items():
        pq, _ = cross_validate(lambda cols=cols: FeatureRanker("all", "logreg", drop=cols), resumes, jobs, labels)
        abl[g] = float(np.nanmean(pq["nDCG@10"]))
    # evidence + related credit: flip the module constants and re-run
    saved = (F.CREDIT_LISTED, F.CREDIT_RELATED)
    pq, _ = cross_validate(lambda: FeatureRanker("all", "logreg", drop=("req_evid",)), resumes, jobs, labels)
    abl["evidence feature (req_evid)"] = float(np.nanmean(pq["nDCG@10"]))
    F.CREDIT_LISTED = 0.8
    pq, _ = cross_validate(lambda: FeatureRanker("all", "logreg"), resumes, jobs, labels)
    abl["discount listed-only skills (listed=0.8)"] = float(np.nanmean(pq["nDCG@10"]))
    F.CREDIT_LISTED, F.CREDIT_RELATED = saved[0], 0.0
    pq, _ = cross_validate(lambda: FeatureRanker("all", "logreg"), resumes, jobs, labels)
    abl["no related-skill credit"] = float(np.nanmean(pq["nDCG@10"]))
    F.CREDIT_LISTED, F.CREDIT_RELATED = saved
    out["ablation_ndcg10"] = {"full": full, **abl}
    md += ["", "## Ablation (SIMRAN v3 logreg, nDCG@10)", "", "| Removed / changed | nDCG@10 | Δ |", "|---|---|---|",
           f"| nothing (full model) | {full:.3f} | — |"]
    md += [f"| {k} | {v:.3f} | {v - full:+.3f} |" for k, v in abl.items()]
    print("ablations done")

    # ---- 3. keyword-stuffing robustness --------------------------------------
    rob = {}
    for rate in [0.0, 0.3, 0.6]:
        b2 = build_benchmark(n_candidates=min(n, 300), seed=args.seed + 7, stuff_rate=rate)
        r2, j2, l2 = prepare(b2)
        stuffer = np.array([c.stuffer for c in b2.candidates])
        rob[rate] = {}
        for name, fac in [("BM25", lambda: baseline_suite()[1]),
                          ("v2 rubric (40/30/20/10)", lambda: baseline_suite()[3]),
                          ("SIMRAN v3 (logreg)", lambda: FeatureRanker("all", "logreg"))]:
            pq, _ = cross_validate(fac, r2, j2, l2)
            nd = pq["nDCG@10"]
            rob[rate][name] = {"all": float(np.nanmean(nd)),
                               "stuffers": float(np.nanmean(nd[stuffer])) if stuffer.any() else None,
                               "honest": float(np.nanmean(nd[~stuffer]))}
    out["stuffing_robustness"] = {str(k): v for k, v in rob.items()}
    md += ["", "## Robustness to keyword stuffing (nDCG@10 on stuffed resumes / honest resumes)", "",
           "| stuff rate | BM25 | v2 rubric | SIMRAN v3 |", "|---|---|---|---|"]
    for rate, d in rob.items():
        cells = []
        for k in ["BM25", "v2 rubric (40/30/20/10)", "SIMRAN v3 (logreg)"]:
            st = d[k]["stuffers"]
            cells.append(f"{st:.3f} / {d[k]['honest']:.3f}" if st is not None else f"– / {d[k]['honest']:.3f}")
        md.append(f"| {rate:.1f} | " + " | ".join(cells) + " |")
    print("robustness done")

    # ---- 4. counterfactual fairness ----------------------------------------
    tr = np.arange(len(resumes)) % 5 != 0
    te = np.where(~tr)[0]
    trained = {
        "TF-IDF cosine": baseline_suite()[0],
        "BM25": baseline_suite()[1],
        "SIMRAN v3 (logreg)": FeatureRanker("all", "logreg"),
    }
    fair = {}
    for name, r in trained.items():
        r.fit([resumes[i] for i in np.where(tr)[0]], [jobs[i] for i in np.where(tr)[0]],
              [labels[i] for i in np.where(tr)[0]])
        fair[name] = {}
        for kind in ["name", "club"]:
            for blind in [False, True]:
                key = f"{kind}{'+redact' if blind else ''}"
                fair[name][key] = counterfactual_test(r, bench, te, TODAY, blind=blind, kind=kind)
    out["counterfactual"] = fair
    md += ["", "## Counterfactual tests (held-out fold). mean |Δscore| as % of slate score range · share of top-5 lists that changed", "",
           "| Method | name swap | name swap + redaction | club swap | club swap + redaction |", "|---|---|---|---|---|"]
    for name, d in fair.items():
        cells = [f"{100 * d[k]['mean_abs_delta']:.2f}% · {100 * d[k]['top5_changed']:.0f}%"
                 for k in ["name", "name+redact", "club", "club+redact"]]
        md.append(f"| {name} | " + " | ".join(cells) + " |")
    print("fairness done")

    # ---- 5. final model for the browser ----------------------------------
    final = FeatureRanker("core", "logreg").fit(resumes, jobs, labels)
    model = {
        "features": final.names,
        "coef": final.clf.coef_[0].round(5).tolist(),
        "intercept": round(float(final.clf.intercept_[0]), 5),
        "mean": final.scaler.mean_.round(5).tolist(),
        "scale": final.scaler.scale_.round(5).tolist(),
        "idf": {k: round(v, 4) for k, v in sorted(final.idf.items())},
        "credit": {"evidenced": F.CREDIT_EVIDENCED, "listed": F.CREDIT_LISTED, "related": F.CREDIT_RELATED},
        "trained_on": f"SIMRAN-Synth seed={args.seed} n={n}",
    }
    out["final_core_weights"] = dict(zip(final.names, model["coef"]))
    (ROOT / "models").mkdir(exist_ok=True)
    if not args.quick:
        (ROOT / "models" / "simran_v3_core.json").write_text(json.dumps(model, indent=1))
    md += ["", "## Learned weights (core model, standardised features)", "", "| feature | weight |", "|---|---|"]
    md += [f"| {k} | {v:+.3f} |" for k, v in sorted(out["final_core_weights"].items(), key=lambda kv: -abs(kv[1]))]

    out["runtime_sec"] = round(time.time() - t0, 1)
    res_dir = ROOT / "results"
    res_dir.mkdir(exist_ok=True)
    suffix = "_quick" if args.quick else ""
    (res_dir / f"benchmark{suffix}.json").write_text(json.dumps(out, indent=1))
    (res_dir / f"tables{suffix}.md").write_text("\n".join(md) + "\n")
    print(f"done in {out['runtime_sec']}s -> results/tables{suffix}.md")


if __name__ == "__main__":
    main()
