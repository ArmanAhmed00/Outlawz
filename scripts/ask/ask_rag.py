import sys, json
sys.path.insert(0, ".")

import faiss
from app.core import INDEX_FILE, CHUNKS_FILE
from app.generation.generate_answer import answer_question


index = faiss.read_index(INDEX_FILE)
with open(CHUNKS_FILE, encoding="utf-8") as f :
    chunks = json.load(f)

query = " ".join(sys.argv[1:]) or input("Question : ")
answer, sources = answer_question(query, index, chunks)
print(answer)
for s in sources:
    print(f"  - {s['source']} p.{s['page']} (score {s['score']:.3f})")