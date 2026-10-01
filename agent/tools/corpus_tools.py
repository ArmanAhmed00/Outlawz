from app.retrieval import retrieve
from app.core import MIN_SCORE

def make_search_corpus(index, chunks):
    def search_corpus(query: str, k: int = 5) -> str:
        """Search the corpus and return relevant passages."""
        results = retrieve(query, index, chunks, k=k)
        if not results or results[0]["score"] < MIN_SCORE:
            return (
                "No relevant information found in the corpus for this query. "
                "Do not answer from your own knowledge — tell the user this "
                "is out of scope."
            )
        return "\n\n".join(
            f"[{r['source']} p.{r['page']} score={r['score']:.2f}]\n{r['text']}"
            for r in results
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