import math

import numpy as np

from simran.evaluate import average_precision, ndcg_at_k, precision_at_k, reciprocal_rank


def test_perfect_ranking_scores_one():
    labels = [3, 2, 1, 0]
    s = [4, 3, 2, 1]
    assert ndcg_at_k(s, labels, 10) == 1.0
    assert average_precision(s, labels) == 1.0
    assert reciprocal_rank(s, labels) == 1.0


def test_ndcg_by_hand():
    # ranking [0, 3]: dcg = 0 + 7/log2(3); ideal = 7
    assert math.isclose(ndcg_at_k([2, 1], [0, 3], 10), (7 / math.log2(3)) / 7)


def test_no_relevant_gives_nan():
    assert np.isnan(average_precision([1, 2], [0, 1]))


def test_precision():
    assert precision_at_k([5, 4, 3, 2, 1, 0], [2, 0, 2, 0, 0, 3], k=5) == 0.4
