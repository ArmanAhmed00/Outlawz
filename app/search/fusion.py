from app.core import RRF_K


def rrf(rankings, k=RRF_K):
    """Reciprocal Rank Fusion: each list gives 1/(k + rank) points per chunk."""
    fused = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            fused[i] = fused.get(i, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused, key=fused.get, reverse=True)