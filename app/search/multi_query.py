"""Retrieve with several queries and merge the results (RRF on the ranked lists)."""
from app.core import TOP_K
from app.search.retrieval import retrieve
from app.search.fusion import rrf


def retrieve_multi(queries, index, chunks, k=TOP_K):
    """One query -> plain retrieve(). Several -> retrieve each, merge by rank (RRF).
    Each chunk keeps its best rerank / FAISS score, so the threshold still works."""
    if len(queries) == 1:
        return retrieve(queries[0], index, chunks, k=k)

    best = {}                                   # chunk idx -> best version of that chunk
    rankings = []
    for q in queries:
        results = retrieve(q, index, chunks, k=k)
        rankings.append([r["idx"] for r in results])
        for r in results:
            old = best.get(r["idx"])
            key = "rerank_score" if "rerank_score" in r else "score"
            if old is None or r[key] > old[key]:
                best[r["idx"]] = r
    merged = [best[i] for i in rrf(rankings)[:k]]
    # results[0] must be the most confident chunk (confidence.py looks at it)
    if merged and "rerank_score" in merged[0]:
        merged.sort(key=lambda r: r["rerank_score"], reverse=True)
    return merged
