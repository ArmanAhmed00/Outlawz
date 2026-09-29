from app.retrieval import retrieve


def make_search_corpus(index, chunks):
    def search_corpus(query: str, k: int = 5) -> str:
        """Cherche dans le corpus et renvoie les passages pertinents."""
        results = retrieve(query, index, chunks, k=k)
        if not results:
            return "No relevant passages found."
        return "\n\n".join(
            f"[{r['source']} p.{r['page']} score={r['score']:.2f}]\n{r['text']}"
            for r in results
        )
    return search_corpus


def make_quote_exact(chunks):
    def quote_exact(source: str, page: int) -> str:
        """Renvoie le texte exact d'un chunk donné (source + page), pour vérifier une citation."""
        matches = [c for c in chunks if c["source"] == source and c["page"] == page]
        if not matches:
            return f"No chunk found for source={source}, page={page}."
        return "\n---\n".join(m["text"] for m in matches)
    return quote_exact