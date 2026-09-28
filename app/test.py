import json
from app.chunking import chunk_corpus

corpus = json.load(open("data/corpus.json"))
chunks = chunk_corpus(corpus)
print(len(chunks), "chunks")
print(chunks[0])
print(chunks[len(chunks)//2])