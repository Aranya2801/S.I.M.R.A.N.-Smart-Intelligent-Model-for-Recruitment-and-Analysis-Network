"""Bag-of-words retrieval baselines. BM25 is written out by hand (it's 30 lines
and I wanted to control the tokenisation so it matches the tf-idf one)."""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

_TOKEN = re.compile(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]")
STOP = set("""a an and are as at be by for from has have in is it its of on or our that the
this to was were will with you your we us they their i me my experience team work years
year using used use etc including strong ability""".split())


_PLACEHOLDER = re.compile(r"\[[A-Z]+\]")   # [NAME], [EMAIL] ... from redact.py


def tokenize(text: str) -> list[str]:
    text = _PLACEHOLDER.sub(" ", text)
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOP]


class TfidfIndex:
    def __init__(self, **kw):
        self.vec = TfidfVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None,
                                   sublinear_tf=True, min_df=1, ngram_range=(1, 2), **kw)

    def fit(self, docs: list[str]):
        self.vec.fit(docs)
        return self

    def cosine(self, query: str, docs: list[str]) -> np.ndarray:
        q = self.vec.transform([query])
        d = self.vec.transform(docs)
        return (d @ q.T).toarray().ravel()   # rows are l2-normalised already


class BM25:
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b

    def fit(self, docs: list[str]):
        toks = [tokenize(d) for d in docs]
        self.N = len(toks)
        self.avgdl = sum(map(len, toks)) / max(1, self.N)
        df = Counter(t for d in toks for t in set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        return self

    def score(self, query: str, docs: list[str]) -> np.ndarray:
        q = Counter(tokenize(query))
        out = np.zeros(len(docs))
        for i, d in enumerate(docs):
            tf = Counter(tokenize(d))
            dl = sum(tf.values())
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                f = tf[t]
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out[i] = s
        return out
