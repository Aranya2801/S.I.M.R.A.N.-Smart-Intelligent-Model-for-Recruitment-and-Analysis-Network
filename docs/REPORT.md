# SIMRAN v3: explainable resume–job matching, and a benchmark to test it

*Aranya Ghosh, technical report, Nov 2026*

## Abstract
Most "AI resume matcher" projects, including SIMRAN v2, send a resume and a job post to an LLM and display whatever score comes back. Nobody can check those scores, they can change from run to run, and they give no evidence of whether the ranking is any good. SIMRAN v3 replaces that with a ten-feature learned ranker whose decisions are visible in the UI, and evaluates it on a synthetic benchmark with graded relevance and realistic text noise. On 600 candidates × 30 jobs, the linear model reaches nDCG@10 = 0.905 and MAP = 0.903. The best baseline, SIMRAN v2's own 40/30/20/10 rubric computed deterministically, reaches 0.874 and 0.843 (paired bootstrap p < 0.001). Ablations show that skill coverage carries most of the signal. Bag-of-words similarity adds almost nothing once structured features are present. Two "evidence weighting" ideas I expected to help did not. Counterfactual name and affiliation swaps change v3 scores by ≤0.01% of the score range, and redaction brings that to zero.

## 1. Problem
Each candidate has a slate of jobs to rank. This is the job-seeker view of recruitment, as opposed to the recruiter ranking many candidates for one job. Relevance is graded:

| Label | Meaning |
|---|---|
| 0 | no fit |
| 1 | weak fit |
| 2 | good fit |
| 3 | strong fit |

Metrics are nDCG@5/10 on the graded labels, plus MAP, MRR and P@5 with label ≥ 2 treated as relevant.

## 2. Why the data is synthetic
I couldn't find a public dataset that has all three of:

- per-job graded labels for the same candidate
- known ground-truth skills, so errors can be diagnosed
- no real personal data

The Kaggle and Hugging Face resume/JD-fit sets have pairwise labels but not slates, and their labels come from annotators who only saw the text. So I wrote a generator, `simran/datasets/synthetic.py`, which works in this order:

1. **Sample a latent candidate:** role (11 tech roles), years of experience (gamma-distributed), seniority, true skill set (core role skills, some from an adjacent role, a couple of generic ones), city, and whether they're open to remote.
2. **Sample a latent job:** role, seniority, minimum years, 3–6 required and 1–3 preferred skills, city or remote.
3. **Compute the label from the latent attributes only:**
   - the score combines required-skill coverage (0.45), preferred coverage (0.10), an experience fit that decays with the shortfall (0.20), role adjacency (0.15) and location (0.10), plus Gaussian noise (σ = 0.05), thresholded into 0–3
   - **hard caps:** a job is never a good fit if the candidate covers less than half the required skills or is more than 3 years short
4. **Only then write the text**, adding the noise that trips up real matchers:
   - aliases and odd casing
   - out-of-vocabulary phrasings the taxonomy can't parse ("kube", "pg", "predictive modelling"), 10% of the time when one exists
   - implicit skills that are true but never written down (8%)
   - keyword stuffing: 4–8 false skills in the skills list for 15% of candidates
   - negated mentions
   - "partnered with the X team" distractors
   - an "our stack includes…" line in job posts that isn't a requirement
   - 20% of job posts written as one paragraph with no headings

Slates are 10 same-role jobs, 8 adjacent-role jobs and 12 random ones, drawn from a pool of 900. Labels are imbalanced, as they would be in reality: 50% are 0 and 25% are 2 or above.

## 3. Methods
**Baselines**

| Method | What it does |
|---|---|
| TF-IDF cosine | uni+bigram, sublinear tf |
| BM25 | k1 = 1.2, b = 0.75, resume as the query |
| Skill Jaccard | overlap of extracted skill sets |
| v2 rubric | 0.4·skill overlap + 0.3·experience + 0.2·title similarity + 0.1·location, exactly the weights the v2 prompt asked the LLM to use, but computed |

**SIMRAN v3** uses 10 core features plus 2 optional text features:

| Feature | Definition |
|---|---|
| `req_cov`, `pref_cov` | IDF-weighted coverage of required and preferred skills. Each skill gets 1.0 if held, 0.5 if only a related skill is held (20 hand-written sibling groups such as {aws, gcp, azure} and {postgresql, mysql}) |
| `req_evid` | same as `req_cov`, but only skills that appear inside a work-experience section count |
| `exp_short`, `exp_over` | shortfall below the minimum years, and years more than 5 above it |
| `sen_under`, `sen_over` | seniority gap between the last title and the job title |
| `title_sim` | Jaccard overlap of title tokens |
| `domain_sim` | cosine between skill-category histograms |
| `loc_ok` | location / remote compatibility |
| `tfidf_cos`, `bm25` | text similarity (BM25 is max-normalised per query) |

Two models are trained to predict label ≥ 2: L2 logistic regression (C = 1) and histogram gradient boosting (200 iterations, 15 leaves). The browser ships the logistic model on the 10 core features, because text features need a fitted corpus.

**Protocol:** 5-fold GroupKFold by candidate, with out-of-fold scores for every query. CIs come from 2000 bootstrap resamples over queries. Significance uses a one-sided paired bootstrap against the best baseline.

## 4. Main results

| Method | nDCG@5 | nDCG@10 | MAP | MRR | P@5 |
|---|---|---|---|---|---|
| TF-IDF cosine | 0.662 | 0.754 | 0.701 | 0.815 | 0.637 |
| BM25 | 0.642 | 0.731 | 0.680 | 0.793 | 0.625 |
| Skill Jaccard | 0.719 | 0.804 | 0.754 | 0.857 | 0.686 |
| v2 rubric | 0.832 | 0.874 | 0.843 | 0.939 | 0.769 |
| v3 logreg (12 feats) | 0.870 | **0.905** | 0.903 | 0.963 | 0.821 |
| v3 logreg (10 core, shipped) | 0.867 | 0.901 | 0.902 | 0.958 | 0.818 |
| v3 GBDT | **0.871** | 0.903 | **0.919** | **0.967** | **0.828** |

- **Retrieval baselines do worst.** TF-IDF and BM25 are clearly the weakest. They reward resumes that share *words* with a post, including the boilerplate stack line, and they can't tell "required" from "nice to have".
- **Most of the gain comes from structure.** The jump from Skill Jaccard to the rubric (+0.07 nDCG@10) is larger than the jump from the rubric to v3 (+0.031). Using years and location at all matters more than how they're weighted.
- **GBDT isn't worth shipping.** It ties logreg on nDCG@10 and is about 1.5 points better on MAP, but it isn't readable and can't be ported to the browser in a few lines.

## 5. Analysis

### 5.1 Ablation (v3 logreg, nDCG@10, full = 0.905)

| Removed | Δ |
|---|---|
| skill features (req_cov, pref_cov, req_evid) | −0.038 |
| location | −0.012 |
| domain_sim | −0.011 |
| experience | −0.009 |
| text features | −0.003 |
| related-skill partial credit | −0.001 |
| seniority / title | ~0 |

Seniority and title barely matter because years of experience already carries the same information here. That might not hold on real data, where titles are messier.

### 5.2 Learned weights (shipped model, standardised)

| Feature | Weight |
|---|---|
| exp_short | −2.59 |
| req_cov | +2.24 |
| domain_sim | +1.45 |
| pref_cov | +0.83 |
| title_sim | +0.38 |
| loc_ok | +0.37 |
| others | \|w\| < 0.06 |

The experience shortfall gets the largest weight. That reflects the hard cap in the label function: being more than 3 years short rules a job out entirely. Real recruiters are more flexible about this, so the weight should be treated as an artefact of the benchmark.

### 5.3 Negative result: evidence weighting
My hypothesis was that skills appearing in experience bullets are more trustworthy than skills that only appear in a list, which should help against keyword stuffing. I tried it two ways:

| Variant | Effect on nDCG@10 |
|---|---|
| discount list-only skills to 0.8 credit | −0.001 |
| separate `req_evid` feature | +0.000 |

Neither helped. `experiments/sweep_listed_credit.py` runs a separate sweep (300 candidates, 30% stuffing, seed 21, 10-feature model):

| Credit for list-only skills | nDCG@10 overall | stuffed resumes |
|---|---|---|
| 1.0 | 0.893 | 0.868 |
| 0.8 | 0.894 | 0.867 |
| 0.6 | 0.892 | 0.867 |
| 0.4 | 0.884 | 0.861 |

Even the *stuffed* resumes didn't benefit: heavy discounting made them rank slightly worse. The reason is that honest candidates also list most of their real skills without writing about them in a bullet (45% in the generator, and probably more in real life). The discount therefore punishes true skills as often as fake ones. I kept `req_evid` in the model because it costs nothing and the UI uses it, but list-only skills get full credit.

### 5.4 Keyword stuffing
nDCG@10, stuffed resumes / honest resumes:

| Stuff rate | BM25 | v2 rubric | v3 |
|---|---|---|---|
| 0.3 | 0.720 / 0.761 | 0.838 / 0.881 | 0.884 / 0.901 |
| 0.6 | 0.713 / 0.750 | 0.863 / 0.857 | 0.884 / 0.885 |

At a 30% stuffing rate, every method ranks stuffed resumes 2–4 points worse, and v3 has the smallest gap. At 60%, the gap almost disappears for v3 and the rubric. Stuffers then make up most of the training data, so this mostly shows that the comparison gets noisy, not that the problem is solved. v3 stays ahead of both baselines throughout. None of the methods really *detects* stuffing. That would take something like checking skills against the projects or roles that should have produced them, which is left as future work.

### 5.5 Counterfactual fairness
On a held-out fold, I changed only the candidate's name (and the matching email) to one from another of five synthetic name groups. Separately, I turned a neutral club ("Engineering Society") into the same club with a group marker ("Women in Engineering Society"). Results are mean |Δscore| as a share of the slate's score range:

| Method | Name | Name + redact | Club | Club + redact |
|---|---|---|---|---|
| TF-IDF | 0.20% | 0 | 0.12% | 0 |
| BM25 | 0 | 0 | 0 | 0 |
| v3 | 0.01% | 0 | <0.01% | 0 |

No top-5 list changed in any setting.

- **TF-IDF moves** because names that appeared in other resumes enter the vocabulary and change the length normalisation.
- **v3 moves only through its two text features.** The shipped core model doesn't read names at all, and with redaction every method is exactly invariant.

This is a narrow test. It checks that the *model* doesn't react to these tokens. It says nothing about bias in the data a deployed model would be trained on, or about proxies the redaction list doesn't cover, such as university names or gaps in employment.

## 6. Limitations and threats to validity
1. **Shared assumptions.** The label function and the features both use the same taxonomy's notion of related skills and the same role/skill pools. A model that knows this taxonomy has an advantage it wouldn't have on real data. The OOV phrasings and implicit skills limit this but don't remove it. Absolute numbers should not be quoted as real-world accuracy.
2. **Templated text.** The generator's text is more regular than real resumes. Parsing errors on real documents will be larger.
3. **The LLM engine is untested.** The optional Claude mode is not evaluated, because it needs a paid API and its output isn't deterministic. Comparing it against v3 on a small, human-labelled real set is the obvious next experiment, and `simran eval-csv` is ready for it.
4. **Single seed.** All numbers come from one benchmark seed (13). An early version of the generator iterated over Python sets, so its output depended on `PYTHONHASHSEED`. That is fixed and covered by a test, and every number here comes from the fixed version. The CIs reflect variance over queries, not over regenerated datasets.

## 7. Reproducing
```
python experiments/run_benchmark.py   # ~3 min on a laptop CPU
```
Everything is seeded. `results/benchmark.json` holds the raw numbers behind every table in this report.
