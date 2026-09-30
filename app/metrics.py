def expected_pages(q):
    """Set of (source, page) where the answer lives, from questions.json."""
    pages = set()
    for e in q.get("expected_chunks") or []:
        ps = e["page"] if isinstance(e["page"], list) else [e["page"]]
        pages.update((e["source"], p) for p in ps)
    return pages


def first_hit_rank(results, expected):
    """1 if the first retrieved chunk is correct, 2 if the second... None if missed."""
    for rank, r in enumerate(results, start=1):
        if (r["source"], r["page"]) in expected:
            return rank
    return None


def recall_at(ranks, k):
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)


def mrr(ranks):
    return sum(1 / r for r in ranks if r is not None) / len(ranks)


def summarize(rows):
    """Recall@k / MRR on questions that have expected chunks, latency on all rows."""
    scored = [r for r in rows if r["has_expected"]]
    if not scored:
        return None
    ranks = [r["rank"] for r in scored]
    return {
        "n": len(ranks),
        "recall@1": recall_at(ranks, 1),
        "recall@3": recall_at(ranks, 3),
        "recall@5": recall_at(ranks, 5),
        "mrr": mrr(ranks),
        "latency": sum(r["latency"] for r in rows) / len(rows),
    }