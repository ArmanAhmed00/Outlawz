import re
import numpy as np
from rank_bm25 import BM25Okapi

_bm25 = None  # built once, then reused


def tokenize(text):
    """'Article 2(2)' -> ['article', '2', '2']"""
    return re.findall(r"\w+", text.lower())


def get_bm25(chunks):
    global _bm25
    if _bm25 is None:
        _bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    return _bm25


def bm25_ids(query, chunks, k):
    """Indices of the k best keyword matches, best first."""
    scores = get_bm25(chunks).get_scores(tokenize(query))
    return np.argsort(scores)[::-1][:k].tolist()