import sys, json
sys.path.insert(0, ".")

import faiss
from app.core import INDEX_FILE, CHUNKS_FILE
from app.retrieval import retrieve

index = faiss.read_index(INDEX_FILE)
with open(CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)

questions = [
    "What is the definition of personal data?",          # dans le corpus
    "What are the obligations for high-risk AI systems?", # dans le corpus
    "What is the recipe for chocolate cake?",             # hors sujet
    "Who won the 2018 football world cup?",               # hors sujet
]

for q in questions:
    results = retrieve(q, index, chunks, k=3)
    print(f"\n=== {q}")
    for r in results:
        print(f"  {r['score']:.3f} | {r['source']} p.{r['page']} | {r['text'][:80]!r}")