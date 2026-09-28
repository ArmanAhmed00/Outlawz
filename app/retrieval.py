import numpy as np
import faiss 
from app.embeddings import get_embeddings



def retrieve(query, index, chunks, k=5, corpus=None):
    query_vector = np.array(get_embeddings([query])).astype("float32")
    faiss.normalize_L2(query_vector)
    fetch_k = k * 5 if corpus else k 
    scores, indeces = index.search(query_vector, fetch_k)

    results = []
    for score, idx in zip(scores[0], indeces[0]):
        if idx == -1:
            continue
        chunk = dict(chunks[idx])
        
        if corpus and chunk["corpus"] != corpus :
            continue
        chunk["score"] = float(score)
        results.append(chunk)

        if len(results) == k :
            break

    return results