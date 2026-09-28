import json
import faiss
from app.retrieval import retrieve

index = faiss.read_index("data/my_index.faiss")
chunks = json.load(open("data/chunks.json"))

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