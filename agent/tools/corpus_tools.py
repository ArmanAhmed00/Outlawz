from app.search.retrieval import retrieve
from app.core import SEARCH_TOP_K
from app.generation.confidence import is_confident

NOTHING_FOUND = "No matching passages found"


def make_search_corpus(index, chunks):
    def search_corpus(query: str, k: int = SEARCH_TOP_K) -> str:
        """Search the corpus. Below the reranker threshold -> a clear 'nothing found' message,
        so the agent can tell a failed search from a good one (and rephrase once)."""
        results = retrieve(query, index, chunks, k=max(k, 1))
        if not is_confident(results):
            return (f"{NOTHING_FOUND} for this query. Rephrase once with the official terms "
                    "of the regulation, or tell the user the documents do not cover it.")
        return "\n\n".join(
            f"[{r['source']} p.{r['page']} rerank={r.get('rerank_score', r['score']):.2f}]\n{r['text']}"
            for r in results[:k]
        )
    return search_corpus



def make_quote_exact(chunks):
    def quote_exact(source: str, page: int) -> str:
        """Renvoie le texte exact d'un chunk donné (source + page), pour vérifier une citation."""
        matches = [c for c in chunks if c["source"] == source and c["page"] == int(page)]
        if not matches:
            return f"No chunk found for source={source}, page={page}."
        return "\n---\n".join(m["text"] for m in matches)
    return quote_exact