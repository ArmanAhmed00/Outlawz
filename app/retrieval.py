import numpy as np
import faiss 
from app.core import TOP_K
from app.embeddings import get_embeddings



def retrieve(query, index, chunks, k=TOP_K):
    query_vector = np.array(get_embeddings([query])).astype("float32")
    faiss.normalize_L2(query_vector)
    scores, indeces = index.search(query_vector, k)

    results = []
    for score, idx in zip(scores[0], indeces[0]):
        if idx == -1:
            continue
        chunk = dict(chunks[idx])
        chunk["score"] = float(score)
        results.append(chunk)

    return results