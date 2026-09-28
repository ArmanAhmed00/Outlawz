import sys, json
sys.path.insert(0, ".")

import faiss
from app.retrieval import retrieve
from app.generation import generate_answer


index = faiss.read_index("data/my_index.faiss")
with open("data/chunks.json") as f :
    chunks = json.load(f)

query = " ".join(sys.argv[1:]) or input("Question : ")
results = retrieve(query, index, chunks, k=5)
print(generate_answer(query, results))