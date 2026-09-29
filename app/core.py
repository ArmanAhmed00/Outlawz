import json
import os


CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"



CHUNK_SIZE = 500
OVERLAP = 100
TOP_K = 5
MIN_SCORE = 0.30  # if the best chunk is less similar than this -> out of scope (tune with evaluate.py)

REFUSAL = "I don't have enough information to answer this."

CORPUS_FILE = "data/corpus.json"
CHUNKS_FILE = "data/chunks.json"
INDEX_FILE = "data/my_index.faiss"
COST_FILE = "data/cost.json"


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


def get_total_cost():
    if not os.path.exists(COST_FILE):
        return 0.0
    with open(COST_FILE) as f:
        return json.load(f)["total"]
