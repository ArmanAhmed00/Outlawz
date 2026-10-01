# Retrieval checker: what does the retriever return for one question? (no answer generated)
# Usage: uv run python scripts/eval/retrieval_checker.py "What is the right to erasure?"
#        add --history "earlier question" (repeatable), --k 10, --no-rerank, --no-bm25
import sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("question", nargs="*", help="question to check (asked interactively if empty)")
parser.add_argument("--history", action="append", default=[], help="earlier user question (repeatable)")
parser.add_argument("--k", type=int, default=None, help="number of chunks to show (default TOP_K)")
parser.add_argument("--no-rerank", action="store_true", help="turn reranking off")
parser.add_argument("--no-bm25", action="store_true", help="turn BM25 off")
args = parser.parse_args()

# set the flags BEFORE retrieval.py is imported (it reads them at import time)
import app.core as core
core.USE_RERANK = not args.no_rerank
core.USE_BM25 = not args.no_bm25

import faiss
from app.search.retrieval import retrieve
from app.generation.rewrite import rewrite_query
from app.generation.confidence import is_confident
from app.eval.metrics import expected_pages, first_hit_rank

index = faiss.read_index(str(ROOT / core.INDEX_FILE))
with open(ROOT / core.CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)
with open(ROOT / core.QUESTIONS_FILE, encoding="utf-8") as f:
    questions = {q["question"]: q for q in json.load(f)}

question = " ".join(args.question) or input("Question : ")
history = [{"role": "user", "content": h} for h in args.history]
k = args.k or core.TOP_K

search_q = rewrite_query(question, history) if core.USE_REWRITE else question
results = retrieve(search_q, index, chunks, k=k)
expected = expected_pages(questions[question]) if question in questions else set()

print(f"\nrerank={core.USE_RERANK} bm25={core.USE_BM25} k={k}")
if search_q != question:
    print(f"Rewritten query: {search_q!r}")
print(f"Expected pages: {sorted(expected) if expected else '-'}\n")

for rank, r in enumerate(results, 1):
    mark = "✅" if any((r["source"], p) in expected for p in r.get("pages", [r["page"]])) else "❌"
    rerank = f"{r['rerank_score']:6.2f}" if "rerank_score" in r else "     -"
    text = " ".join(r["text"].split())[:150]
    print(f"{rank:2}. {mark} {r['source'][:40]} p.{r['page']:<4} faiss {r['score']:.3f} | rerank {rerank}")
    print(f"      {text}...")

# ---------------- Verdict ----------------
print()
if not expected:
    print("No expected chunks for this question")
else:
    rank = first_hit_rank(results, expected)
    if rank:
        print(f"Expected page found at rank {rank}")
    else:
        print("MISSED: expected " + ", ".join(f"{s} p.{p}" for s, p in sorted(expected)))

if is_confident(results):
    print(f"Would answer (top rerank score >= threshold {core.RERANK_THRESHOLD})")
else:
    top = results[0].get("rerank_score") if results else None
    print(f"Would REFUSE (top rerank score {top:.2f} < threshold {core.RERANK_THRESHOLD})"
          if top is not None else "Would REFUSE (low FAISS score / no results)")
