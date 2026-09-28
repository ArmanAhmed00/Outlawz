from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv
import json
import os
import time
import faiss
import numpy as np
import tiktoken

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"



CHUNK_SIZE = 500
OVERLAP = 100
TOP_K = 5
MIN_SCORE = 0.30  # if the best chunk is less similar than this -> out of scope (tune with evaluate.py)

REFUSAL = "I don't have enough information to answer this."

CORPUS_FILE = "data/corpus.json"
CHUNKS_FILE = "data/chunks.json"
INDEX_FILE = "data/index.faiss"
COST_FILE = "data/cost.json"
EMBED_BATCH = 100

enc = tiktoken.get_encoding("cl100k_base")
 
 
# ---------------- Section 8: Cost tracker ----------------
def track_cost(response, is_embedding=False):
    usage = response.usage
    if is_embedding:
        cost = usage.total_tokens * 0.02 / 1_000_000
    else:  # chat (gpt-4o-mini)
        cost = (usage.prompt_tokens * 0.15 + usage.completion_tokens * 0.60) / 1_000_000
    if os.path.exists(COST_FILE):
        with open(COST_FILE) as f:
            data = json.load(f)
    else:
        data = {"total": 0.0}
    data["total"] += cost
    with open(COST_FILE, "w") as f:
        json.dump(data, f)
    print(f"This call: ${cost:.6f} | Team total: ${data['total']:.4f} / $5.00")
 
 
# ---------------- Section 4: Chat with retry ----------------
def safe_chat(messages, max_tokens=300, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL, messages=messages, temperature=0, max_tokens=max_tokens
            )
            track_cost(response)
            return response
        except RateLimitError:
            time.sleep(2 ** attempt)
        except APIError as e:
            print(f"API error: {e}")
            time.sleep(1)
    return None  # always check: if response is None: handle error
 
 

def get_embeddings(texts):
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    track_cost(response, is_embedding=True)
    return [item.embedding for item in response.data]


def get_total_cost():
    if not os.path.exists(COST_FILE):
        return 0.0
    with open(COST_FILE) as f:
        return json.load(f)["total"]


# ---------------- Chunking ----------------
def chunk_corpus(entries):
    """Split each page into CHUNK_SIZE-token windows overlapping by OVERLAP tokens."""
    chunks = []
    step = CHUNK_SIZE - OVERLAP
    for e in entries:
        tokens = enc.encode(e["text"])
        for start in range(0, len(tokens), step):
            chunks.append({
                "source": e["source"],
                "page": e["page"],
                "text": enc.decode(tokens[start:start + CHUNK_SIZE]),
            })
            if start + CHUNK_SIZE >= len(tokens):
                break
    return chunks


# ---------------- Index ----------------
def _normalize(vectors):
    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)  # inner product on unit vectors == cosine similarity
    return arr


def build_index():
    with open(CORPUS_FILE, encoding="utf-8") as f:
        chunks = chunk_corpus(json.load(f))
    vectors = []
    for i in range(0, len(chunks), EMBED_BATCH):
        vectors.extend(get_embeddings([c["text"] for c in chunks[i:i + EMBED_BATCH]]))
    vectors = _normalize(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, INDEX_FILE)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)
    return index, chunks


def load_index():
    """Load the cached index, building it (one embedding pass) if missing."""
    if not (os.path.exists(INDEX_FILE) and os.path.exists(CHUNKS_FILE)):
        return build_index()
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)
    return faiss.read_index(INDEX_FILE), chunks


# ---------------- Retrieval + answer ----------------
def retrieve(question, index, chunks, top_k=TOP_K):
    query = _normalize(get_embeddings([question]))
    scores, ids = index.search(query, top_k)
    return [{**chunks[i], "score": float(s)} for s, i in zip(scores[0], ids[0]) if i != -1]


def answer(question, index, chunks, top_k=TOP_K, min_score=MIN_SCORE):
    """Returns (answer_text, hits). Refuses if the best hit is below min_score."""
    hits = retrieve(question, index, chunks, top_k)
    if not hits or hits[0]["score"] < min_score:
        return REFUSAL, hits

    context = "\n\n".join(
        f"[{n}] ({h['source']}, p.{h['page']})\n{h['text']}" for n, h in enumerate(hits, start=1)
    )
    messages = [
        {"role": "system", "content": (
            "Answer the question using only the numbered context passages. "
            "Cite passages inline like [1] or [2][3]. "
            f'If the context does not contain the answer, reply exactly: "{REFUSAL}"'
        )},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    response = safe_chat(messages)
    if response is None:
        return "The model request failed. Please try again.", hits
    return response.choices[0].message.content or REFUSAL, hits
