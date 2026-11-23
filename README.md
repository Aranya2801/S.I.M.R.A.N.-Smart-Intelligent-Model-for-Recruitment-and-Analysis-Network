# S.I.M.R.A.N.
**Smart Intelligent Model for Recruitment and Analysis Network**

Explainable resume ↔ job matching, plus a benchmark to check whether it actually works.

Paste a resume and a few job postings and you get a ranked list. Every score comes with what helped it, what pulled it down, and which required skills are missing. The web app runs entirely in the browser: no API key, and nothing is uploaded.

> **v3 is a rewrite.** v2 sent everything to an LLM with a "score it 40/30/20/10" prompt. That made the scores impossible to verify, and the deployed page was broken anyway (see [What changed from v2](#what-changed-from-v2)). v3 replaces the prompt with a small learned ranker over features you can inspect, and adds the evaluation that v2 never had.

---

## Results

5-fold grouped cross-validation on **SIMRAN-Synth** (600 candidates × 30 jobs, graded relevance 0–3). 95% bootstrap CIs are in [`results/tables.md`](results/tables.md).

| Method | nDCG@10 | MAP | P@5 |
|---|---|---|---|
| TF-IDF cosine | 0.754 | 0.701 | 0.637 |
| BM25 | 0.731 | 0.680 | 0.625 |
| Skill Jaccard | 0.804 | 0.754 | 0.686 |
| v2 rubric (40/30/20/10, computed instead of prompted) | 0.874 | 0.843 | 0.769 |
| **SIMRAN v3 (logistic regression)** | **0.905** | 0.903 | 0.821 |
| SIMRAN v3 (gradient boosting) | 0.903 | **0.919** | **0.828** |

Both v3 models beat the strongest baseline on nDCG@10 and MAP (paired bootstrap, p < 0.001). The linear model is what ships: it's as good on nDCG and you can read its weights.

**These numbers come from synthetic data.** They show which design choices matter relative to each other. They don't tell you how accurate the model is on real resumes. [`docs/REPORT.md`](docs/REPORT.md) explains why the data is synthetic and what that means, and `simran eval-csv` lets you run the model on a real labelled set.

Other findings, each covered in the report:
- **Skill coverage does most of the work.** Removing the skill features costs 0.038 nDCG@10. Location (−0.012), domain fit (−0.011) and experience (−0.009) come next. Seniority and title similarity add almost nothing once skills and years are in.
- **Text similarity is nearly redundant.** Adding TF-IDF and BM25 on top of the structured features changes nDCG@10 by 0.003.
- **Negative result:** two ways of rewarding skills that appear in actual work bullets (rather than just the skills list) did *not* help on this data. Details in §5.3.
- **Counterfactual tests:** swapping a candidate's name between demographic groups, or adding a group marker to a club membership, moves TF-IDF scores slightly and v3 scores barely at all. Blind-screening redaction brings both to exactly zero, and no top-5 list changed in any setting.

---

## Quick start

### Web app (no install)
Open `web/index.html` in a browser, then click *New Analysis → Load Sample Resume → Load Sample Jobs → Run*.

To host it, push to `main` and set **Settings → Pages → Source: GitHub Actions**. The workflow in `.github/workflows/pages.yml` publishes the `web/` folder.

Settings has an optional **Claude API** engine (the v2 behaviour) if you paste in your own Anthropic key. It isn't part of the benchmark.

### Python
```bash
pip install -e ".[dev]"

python -m simran match --resume examples/resume.txt --jobs examples/jobs.json --blind
```
```
candidate: ~6.4 yrs, 27 skills found (12 backed by experience bullets)

 1.  99.2  [High  ] Senior Full Stack Engineer @ Stripe
      missing: distributed systems, graphql
      for: covers most required skills, skill profile fits the domain
 2.  99.0  [High  ] Full Stack Engineer @ Notion
 ...
 7.   0.1  [Low   ] Data Scientist @ Meta
      missing: a/b testing, hadoop, pandas, pytorch, scikit-learn, spark, statistics, tensorflow
      against: skill profile is from a different domain, missing several required skills
```

### Reproduce the paper numbers
```bash
python experiments/run_benchmark.py          # ~3 min, writes results/ and models/
python scripts/export_web_assets.py          # copies the new weights into the web app
pytest -q                                    # includes a JS-vs-python parity test (needs node)
```

### Your own data
```bash
python -m simran eval-csv my_pairs.csv       # columns: resume_text, job_description_text, label
```
`label` can be 0/1/2 or `No Fit / Potential Fit / Good Fit`. That's the format of the public resume/JD-fit datasets on Hugging Face.

---

## How it works

```
resume text ─┐                    ┌─ required skills ─┐
             ├─ parsing.py ───────┤  nice-to-haves    ├─ features.py ─ logistic ─ score 0–100
job text ────┘  (taxonomy.py)     │  years, seniority │   (10 feats)   regression   + reasons
                                  └─ location, titles ┘
```

1. **Skill extraction** (`taxonomy.py`) matches against a 101-skill taxonomy with aliases (k8s → kubernetes, Postgres → postgresql). Longer aliases take priority (React Native isn't also counted as React). Negated mentions like "no experience with Kafka" are ignored. Short ambiguous words such as *go*, *R* and *rest* only count inside a skills list or when capitalised mid-sentence.
2. **Parsing** (`parsing.py`) splits job posts into *required* and *nice-to-have* sections and skips "about us / our stack" boilerplate. It also merges overlapping date ranges to get years of experience, reads seniority from titles, and works out the remote/location situation.
3. **Features** (`features.py`):
   - IDF-weighted coverage of required and preferred skills, with partial credit for a closely related skill (MySQL when they ask for Postgres)
   - experience shortfall and over-qualification
   - seniority gap
   - title overlap
   - skill-domain cosine
   - location fit
4. **Ranker** (`rankers.py`) is a logistic regression trained to predict "good match" (label ≥ 2). Its probability is the 0–100 score, and each feature's `weight × standardised value` is the explanation shown in the UI.
5. **Blind mode** (`redact.py`) removes names, contact details, links, pronouns and a few affiliation phrases before anything gets scored.

The browser engine (`web/js/engine.js`) is a line-for-line port of steps 1–4. `tests/test_web_parity.py` runs both versions on the same inputs and fails if any score differs by more than 1e-6.

## Repo layout
```
simran/            python package (parsing, features, rankers, evaluation, fairness, CLI)
  data/skills.json   skill taxonomy, shared with the web app
  datasets/          SIMRAN-Synth generator
experiments/       run_benchmark.py, reproduces every table
results/           benchmark.json + tables.md from the last full run
models/            exported core model weights (used by CLI + web)
web/               the app (index.html, css/, js/, assets/)
docs/REPORT.md     write-up: method, data, results, limitations
tests/             pytest suite
```

## What changed from v2
- **The deployed page was broken.** `index.html` loaded `css/` and `js/` paths, but every file was committed flat to the repo root, so the page had no styles or scripts. The files now live in `web/`.
- **The API call could never succeed.** It hit `api.anthropic.com` from the browser with no `x-api-key` or `anthropic-version` header. Claude mode now sends the proper headers and uses a key you supply; it's opt-in.
- The duplicate `index new.html` is gone.
- Scoring is no longer whatever the LLM returned. The 40/30/20/10 split was a guess, so v3 learns its weights and evaluates them against baselines.

## Limitations
I'd rather list these myself than have a reviewer find them:
- The benchmark is synthetic, and its label function shares the taxonomy's idea of "related" skills with the features. Report §6 covers this in detail.
- The taxonomy has 101 skills and is tech-focused. Non-software roles will mostly come out as "no skills found".
- Parsing assumes English resumes with fairly standard section headings.
- The domain-fit feature can be harsh on generalists. In the example above, a full-stack React/TypeScript candidate scores only 15 for a pure frontend role.
- The fairness tests measure *score sensitivity* to names and affiliations. They don't show that the system is fair in deployment.

## License
MIT
