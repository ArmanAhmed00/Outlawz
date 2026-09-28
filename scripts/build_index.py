import sys, json
sys.path.insert(0, ".")

import numpy as np
import faiss
from app.chunking import chunk_corpus
from app.embeddings import embed_chunks

with open("data/corpus.json") as f:
    corpus = json.load(f)

chunks = chunk_corpus(corpus)
print(f"{len(chunks)} chunks created")

vectors = np.array(embed_chunks(chunks)).astype("float32")
faiss.normalize_L2(vectors)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)

faiss.write_index(index, "data/my_index.faiss")
with open("data/chunks.json", "w") as f :
    json.dump(chunks, f, ensure_ascii=False)

print("Index and chunks saved ")

