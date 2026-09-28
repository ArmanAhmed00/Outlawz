
def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text) :
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap
    return chunks



def chunk_corpus(corpus, chunk_size=500, overlap=100):
    chunks = []
    for entry in corpus:
        for i, chunk in enumerate(chunk_text(entry["text"], chunk_size, overlap)):
            chunks.append({
                "page" : entry["page"],
                "source" : entry["source"],
                "char_count" : entry["char_count"],
                "text": chunk,
            })

    return chunks 