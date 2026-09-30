import numpy as np
import faiss
from app.embeddings import get_embeddings


def embed_query(query):
    qv = np.array(get_embeddings([query])).astype("float32")
    faiss.normalize_L2(qv)
    return qv


def vector_ids(qv, index, k):
    """Indices of the k closest chunks, best first."""
    _, ids = index.search(qv, k)
    return [int(i) for i in ids[0] if i != -1]


def to_result(i, chunks, index, qv):
    """Chunk dict + its cosine score (works even for chunks only BM25 found)."""
    chunk = dict(chunks[i])
    chunk["idx"] = i
    chunk["score"] = float(np.dot(index.reconstruct(i), qv[0]))
    return chunk