from app.core import TOP_K, FETCH_K, USE_RERANK, USE_BM25, RERANK_BACKEND # type: ignore
from app.search.vector_search import embed_query, vector_ids, to_result
from app.search.bm25 import bm25_ids
from app.search.fusion import rrf
from app.search.rerank import rerank
from app.search.jev_rerank import jev_rerank


def retrieve(query, index, chunks, k=TOP_K):
    """Vector search (+ BM25 with RRF) (+ reranking), depending on the flags."""
    qv = embed_query(query)
    n = FETCH_K if (USE_RERANK or USE_BM25) else k

    ids = vector_ids(qv, index, n)
    if USE_BM25:
        ids = rrf([ids, bm25_ids(query, chunks, n)])[:n]

    candidates = [to_result(i, chunks, index, qv) for i in ids]
    if USE_RERANK:
        reranker = jev_rerank if RERANK_BACKEND == "jev" else rerank
        return reranker(query, candidates, k)
    return candidates[:k]