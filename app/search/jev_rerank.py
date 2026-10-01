
import os


def jev_scores(query, texts):
    """One relevance probability (0-1) per text.
    TODO: replace with the real Jev API call once you have access + docs
    (put the key in .env as JEV_API_KEY, never in the code)."""
    if not os.getenv("JEV_API_KEY"):
        raise RuntimeError("JEV_API_KEY missing in .env - Jev needs early access")
    raise NotImplementedError("Add the Jev API call here (see TypeSafe AI docs)")


def jev_rerank(query, candidates, k):
    """Same interface as rerank(): sets c['rerank_score'], returns the best k."""
    if not candidates:
        return []
    scores = jev_scores(query, [c["text"] for c in candidates])
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)   # same key -> threshold, eval and UI keep working
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:k]
