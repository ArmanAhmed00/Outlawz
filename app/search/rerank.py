from sentence_transformers import CrossEncoder
from app.core import RERANK_MODEL

_model = None  # loaded once, reused for every question


def get_reranker():
    global _model
    if _model is None:
        _model = CrossEncoder(RERANK_MODEL)
    return _model


def rerank(query, candidates, k):
    """Score each (question, chunk) pair with the cross-encoder, keep the best k."""
    if not candidates:
        return []
    pairs = [(query, c["text"]) for c in candidates]
    scores = get_reranker().predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:k]