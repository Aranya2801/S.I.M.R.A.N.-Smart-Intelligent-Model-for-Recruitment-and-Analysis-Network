"""Command line entry point.

    python -m simran match --resume me.txt --jobs jobs.json [--blind]
    python -m simran eval-csv pairs.csv      # your own labelled (resume, job, label) pairs

jobs.json is a list of {"title", "company", "location", "description"} objects
(same shape the web app exports).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from .model import CoreModel, DEFAULT_MODEL
from .parsing import parse_job, parse_resume
from .redact import redact


def cmd_match(a):
    text = Path(a.resume).read_text(encoding="utf-8")
    if a.blind:
        text = redact(text)
    res = parse_resume(text)
    raw = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    jobs = []
    for j in raw:
        pj = parse_job(j.get("title", ""), j.get("description", ""), j.get("location", ""))
        pj.extra["company"] = j.get("company", "")
        jobs.append(pj)
    model = CoreModel.load(a.model)
    matches = model.match(res, jobs)
    if a.json:
        print(json.dumps([{
            "job_title": m.job.title, "company": m.job.extra.get("company", ""), "score": round(m.score, 1),
            "match_level": m.level, "missing_skills": m.missing,
            "matched": [s for s, _ in m.matched], "reasons": m.reasons} for m in matches], indent=2))
        return
    print(f"candidate: ~{res.years} yrs, {len(res.skills)} skills found "
          f"({len(res.evidenced)} backed by experience bullets)\n")
    for i, m in enumerate(matches, 1):
        co = m.job.extra.get("company")
        print(f"{i:>2}. {m.score:5.1f}  [{m.level:<6}] {m.job.title}" + (f" @ {co}" if co else ""))
        if m.missing:
            print(f"      missing: {', '.join(m.missing)}")
        good = [n for n, c in m.reasons if c > 0.15][:2]
        bad = [n for n, c in m.reasons if c < -0.15][:2]
        if good:
            print(f"      for: {', '.join(good)}")
        if bad:
            print(f"      against: {', '.join(bad)}")


LABEL_MAP = {"no fit": 0, "potential fit": 1, "good fit": 2}


def cmd_eval_csv(a):
    """Pointwise evaluation on a CSV of labelled pairs. Columns: resume_text,
    job_description_text, label (int, or No Fit / Potential Fit / Good Fit).
    Reports ROC-AUC (label >= threshold) and Spearman for each unsupervised scorer
    plus the shipped core model. Doesn't retrain anything."""
    import csv

    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score

    from .rankers import SkillJaccardRanker, RuleRanker
    from .text import TfidfIndex

    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    y = np.array([int(r["label"]) if r["label"].strip().isdigit() else LABEL_MAP[r["label"].strip().lower()]
                  for r in rows])
    res = [parse_resume(r["resume_text"]) for r in rows]
    jobs = [parse_job("", r["job_description_text"]) for r in rows]
    tf = TfidfIndex().fit([r["resume_text"] for r in rows] + [r["job_description_text"] for r in rows])
    model = CoreModel.load(a.model)
    scores = {
        "TF-IDF cosine": [tf.cosine(r.text, [j.text])[0] for r, j in zip(res, jobs)],
        "Skill Jaccard": [SkillJaccardRanker().score(r, [j])[0] for r, j in zip(res, jobs)],
        "v2 rubric": [RuleRanker().score(r, [j])[0] for r, j in zip(res, jobs)],
        "SIMRAN v3 core (shipped weights)": [model.score(r, j) for r, j in zip(res, jobs)],
    }
    yb = (y >= a.threshold).astype(int)
    print(f"{len(rows)} pairs, positives (label>={a.threshold}): {yb.sum()}")
    for k, s in scores.items():
        auc = roc_auc_score(yb, s) if 0 < yb.sum() < len(yb) else float("nan")
        print(f"  {k:34s} AUC={auc:.3f}  spearman={spearmanr(s, y).statistic:.3f}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="simran")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match", help="rank jobs for one resume")
    m.add_argument("--resume", required=True)
    m.add_argument("--jobs", required=True)
    m.add_argument("--model", default=str(DEFAULT_MODEL))
    m.add_argument("--blind", action="store_true", help="redact name/contact/affiliations first")
    m.add_argument("--json", action="store_true")
    m.set_defaults(fn=cmd_match)
    e = sub.add_parser("eval-csv", help="evaluate on your own labelled pairs")
    e.add_argument("csv")
    e.add_argument("--model", default=str(DEFAULT_MODEL))
    e.add_argument("--threshold", type=int, default=2)
    e.set_defaults(fn=cmd_eval_csv)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
