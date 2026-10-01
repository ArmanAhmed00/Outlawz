# Build the Article-aware index (does NOT touch the original data/chunks.json + my_index.faiss).
# Usage: uv run python scripts/ingest/build_article_index.py   (~$0.01 of embeddings)
# Then use it with CHUNKING = "article" in app/core.py, or eval_runner.py --chunking article
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import faiss
import app.core as core
from app.article_chunking import chunk_corpus_by_article
from app.embeddings import embed_chunks

with open(ROOT / core.CORPUS_FILE, encoding="utf-8") as f:
    corpus = json.load(f)

chunks = chunk_corpus_by_article(corpus)
print(f"{len(chunks)} article-aware chunks "
      f"({sum(c['article'] is not None for c in chunks)} inside an Article)")

vectors = np.array(embed_chunks(chunks)).astype("float32")
faiss.normalize_L2(vectors)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)

faiss.write_index(index, str(ROOT / core.ARTICLE_INDEX_FILE))
with open(ROOT / core.ARTICLE_CHUNKS_FILE, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False)
print(f"Saved {core.ARTICLE_INDEX_FILE} and {core.ARTICLE_CHUNKS_FILE}")
