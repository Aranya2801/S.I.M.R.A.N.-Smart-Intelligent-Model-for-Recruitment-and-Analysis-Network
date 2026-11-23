## Main results (5-fold grouped CV, mean and 95% bootstrap CI)

| Method | nDCG@5 | nDCG@10 | MAP | MRR | P@5 |
|---|---|---|---|---|---|
| TF-IDF cosine | 0.662 (0.646–0.677) | 0.754 (0.743–0.765) | 0.701 (0.682–0.720) | 0.815 (0.791–0.839) | 0.637 (0.611–0.661) |
| BM25 | 0.642 (0.626–0.657) | 0.731 (0.720–0.743) | 0.680 (0.660–0.698) | 0.793 (0.767–0.817) | 0.625 (0.599–0.649) |
| Skill Jaccard | 0.719 (0.705–0.733) | 0.804 (0.795–0.814) | 0.754 (0.735–0.772) | 0.857 (0.835–0.878) | 0.686 (0.663–0.709) |
| v2 rubric (40/30/20/10) | 0.832 (0.821–0.843) | 0.874 (0.866–0.881) | 0.843 (0.827–0.858) | 0.939 (0.923–0.953) | 0.769 (0.747–0.792) |
| SIMRAN v3 (logreg) | 0.870 (0.860–0.880) | 0.905 (0.898–0.911) | 0.903 (0.890–0.915) | 0.963 (0.951–0.974) | 0.821 (0.801–0.842) |
| SIMRAN v3 (logreg) core | 0.867 (0.857–0.877) | 0.901 (0.895–0.908) | 0.902 (0.889–0.914) | 0.958 (0.946–0.970) | 0.818 (0.797–0.839) |
| SIMRAN v3 (GBDT) | 0.871 (0.861–0.881) | 0.903 (0.897–0.910) | 0.919 (0.907–0.930) | 0.967 (0.956–0.977) | 0.828 (0.807–0.848) |

Best baseline: **v2 rubric (40/30/20/10)**. Paired bootstrap p-values (one-sided, v3 > baseline): SIMRAN v3 (logreg): nDCG@10 p=0.0000, MAP p=0.0000; SIMRAN v3 (GBDT): nDCG@10 p=0.0000, MAP p=0.0000

## Ablation (SIMRAN v3 logreg, nDCG@10)

| Removed / changed | nDCG@10 | Δ |
|---|---|---|
| nothing (full model) | 0.905 | — |
| skills | 0.866 | -0.038 |
| experience | 0.896 | -0.009 |
| seniority | 0.905 | +0.000 |
| title | 0.906 | +0.001 |
| domain | 0.893 | -0.011 |
| location | 0.892 | -0.012 |
| text (tf-idf+bm25) | 0.901 | -0.003 |
| evidence feature (req_evid) | 0.904 | -0.000 |
| discount listed-only skills (listed=0.8) | 0.904 | -0.001 |
| no related-skill credit | 0.904 | -0.001 |

## Robustness to keyword stuffing (nDCG@10 on stuffed resumes / honest resumes)

| stuff rate | BM25 | v2 rubric | SIMRAN v3 |
|---|---|---|---|
| 0.0 | – / 0.740 | – / 0.866 | – / 0.906 |
| 0.3 | 0.720 / 0.761 | 0.838 / 0.881 | 0.884 / 0.901 |
| 0.6 | 0.713 / 0.750 | 0.863 / 0.857 | 0.884 / 0.885 |

## Counterfactual tests (held-out fold). mean |Δscore| as % of slate score range · share of top-5 lists that changed

| Method | name swap | name swap + redaction | club swap | club swap + redaction |
|---|---|---|---|---|
| TF-IDF cosine | 0.20% · 0% | 0.00% · 0% | 0.12% · 0% | 0.00% · 0% |
| BM25 | 0.00% · 0% | 0.00% · 0% | 0.00% · 0% | 0.00% · 0% |
| SIMRAN v3 (logreg) | 0.01% · 0% | 0.00% · 0% | 0.00% · 0% | 0.00% · 0% |

## Learned weights (core model, standardised features)

| feature | weight |
|---|---|
| exp_short | -2.588 |
| req_cov | +2.241 |
| domain_sim | +1.450 |
| pref_cov | +0.829 |
| title_sim | +0.382 |
| loc_ok | +0.373 |
| exp_over | -0.051 |
| req_evid | -0.020 |
| sen_under | +0.018 |
| sen_over | -0.008 |
