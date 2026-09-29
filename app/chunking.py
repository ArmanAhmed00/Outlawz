from app.core import CHUNK_SIZE, OVERLAP


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    start = 0
    while start < len(text) :
        chunk = text[start:start + chunk_size].strip()
        if len(chunk) >= 50 :
            chunks.append(chunk)

        start += chunk_size - overlap
    return chunks



def chunk_corpus(corpus, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    for entry in corpus:
        for chunk in chunk_text(entry["text"], chunk_size, overlap):
            chunks.append({
                "page" : entry["page"],
                "source" : entry["source"],
                "char_count" : entry["char_count"],
                "text": chunk,
            })

    return chunks 