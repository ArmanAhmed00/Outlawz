from app.core import RERANK_THRESHOLD, MIN_SCORE


def is_confident(results):
    """False when even the best chunk is too weak -> the system should refuse."""
    if not results:
        return False
    if "rerank_score" in results[0]:
        # reranker on: results are sorted, so results[0] is the best match
        return results[0]["rerank_score"] >= RERANK_THRESHOLD
    # reranker off (ablation runs): fall back to the FAISS cosine score
    return max(r["score"] for r in results) >= MIN_SCORE
