# Retrieval only (cheap):  uv run python scripts/eval/eval_runner.py
# Full (with answers):     uv run python scripts/eval/eval_runner.py --full
# Ablation rows:           add --no-rerank and/or --no-bm25
import sys, json, time, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import RESULTS_DIR

parser = argparse.ArgumentParser()
parser.add_argument("--full", action="store_true", help="also generate answers")
parser.add_argument("--no-rerank", action="store_true", help="turn reranking off")
parser.add_argument("--no-bm25", action="store_true", help="turn BM25 off")
parser.add_argument("--no-rewrite", action="store_true", help="turn query rewriting off")
parser.add_argument("--decompose", action="store_true", help="split multi-part questions")
parser.add_argument("--expand", action="store_true", help="also search with 2 rephrasings")
parser.add_argument("--no-clarify", action="store_true", help="never ask to clarify (full mode)")
parser.add_argument("--chunking", choices=["fixed", "article"], default=None,
                    help="which index to use (default: CHUNKING in app/core.py)")
parser.add_argument("--out", default=f"{RESULTS_DIR}/eval_results.json")
args = parser.parse_args()

# set the flags BEFORE retrieval.py is imported (it reads them at import time)
import app.core as core
core.USE_RERANK = not args.no_rerank
core.USE_BM25 = not args.no_bm25
core.USE_REWRITE = not args.no_rewrite
core.USE_DECOMPOSE = args.decompose
core.USE_EXPANSION = args.expand
core.USE_CLARIFY = not args.no_clarify
if args.chunking == "article":
    core.CHUNKS_FILE, core.INDEX_FILE = core.ARTICLE_CHUNKS_FILE, core.ARTICLE_INDEX_FILE
elif args.chunking == "fixed":
    core.CHUNKS_FILE, core.INDEX_FILE = "data/chunks.json", "data/my_index.faiss"

import faiss
from app.search.retrieval import retrieve
from app.generation.generate_answer import answer_question
from app.eval.metrics import expected_pages, first_hit_rank, summarize
from app.generation.rewrite import rewrite_query
from app.generation.query_planner import plan_queries
from app.search.multi_query import retrieve_multi
from app.generation.clarify import CLARIFY_PREFIX

index = faiss.read_index(str(ROOT / core.INDEX_FILE))
with open(ROOT / core.CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)
with open(ROOT / core.QUESTIONS_FILE, encoding="utf-8") as f:
    questions = [q for q in json.load(f) if q["category"] != "agent"]  # agent questions: agent_eval_runner.py

print(f"Mode: {'full' if args.full else 'retrieval only'} | "
      f"rerank={core.USE_RERANK} bm25={core.USE_BM25} rewrite={core.USE_REWRITE} "
      f"decompose={core.USE_DECOMPOSE} expand={core.USE_EXPANSION} "
      f"clarify={core.USE_CLARIFY} index={core.INDEX_FILE}")
retrieve("warm up", index, chunks)  # load reranker + BM25 before timing

# ---------------- Run every question ----------------
rows = []
for i, q in enumerate(questions, 1):
    t0 = time.perf_counter()
    history = [{"role": "user", "content": h} for h in q.get("history", [])]
    search_q = rewrite_query(q["question"], history) if core.USE_REWRITE else q["question"]
    queries = plan_queries(search_q)
    results = retrieve_multi(queries, index, chunks)
    expected = expected_pages(q)

    row = {
        "question": q["question"],
        "category": q["category"],
        "sub_type": q.get("sub_type"),
        "difficulty": q.get("difficulty"),
        "priority": q.get("priority", False),
        "is_followup": bool(history),
        "rewritten_query": search_q if history else None,
        "queries": queries if len(queries) > 1 else None,
        "has_expected": bool(expected),
        "rank": first_hit_rank(results, expected) if expected else None,
        "top_rerank": results[0].get("rerank_score") if results else None,
        "retrieved": [
            {"source": r["source"], "page": r["page"],
             "faiss": round(r["score"], 3),
             "rerank": round(r["rerank_score"], 2) if "rerank_score" in r else None}
            for r in results
        ],
    }

    if args.full:
        answer, _ = answer_question(q["question"], index, chunks, results=results, history=history)
        row["answer"] = answer
        row["expected_answer"] = q.get("expected_answer")
        row["clarified"] = answer.startswith(CLARIFY_PREFIX)
        # a clarification counts as "not answering": right for vague questions, wrong otherwise
        row["refused"] = core.REFUSAL.lower().rstrip(".") in answer.lower() or row["clarified"]
        row["correct"] = None  # fill in by hand after reading the answer: true / false

    row["latency"] = round(time.perf_counter() - t0, 2)
    rows.append(row)
    print(f"[{i:2}/{len(questions)}] rank={row['rank']} {row['latency']}s | {q['question'][:65]}")


# ---------------- Scorecard ----------------
def table(title, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    print(f"\n--- {title} ---")
    print(f"{'':18} {'n':>3} {'R@1':>6} {'R@3':>6} {'R@5':>6} {'MRR':>6} {'lat(s)':>7}")
    for name, rs in groups.items():
        s = summarize(rs)
        if s:
            print(f"{str(name):18} {s['n']:>3} {s['recall@1']:>6.0%} {s['recall@3']:>6.0%} "
                  f"{s['recall@5']:>6.0%} {s['mrr']:>6.2f} {s['latency']:>7.2f}")


overall = summarize(rows)
print("\n===== OVERALL =====")
print(f"Recall@1 {overall['recall@1']:.0%} | Recall@3 {overall['recall@3']:.0%} | "
      f"Recall@5 {overall['recall@5']:.0%} | MRR {overall['mrr']:.2f} | "
      f"avg latency {overall['latency']:.2f}s  (on {overall['n']} questions)")
table("By category", "category")
table("By difficulty", "difficulty")

followups = [r for r in rows if r["is_followup"]]
if followups and summarize(followups):
    s_fu = summarize(followups)
    print(f"\n--- Follow-up questions ---")
    print(f"R@1 {s_fu['recall@1']:.0%} | R@5 {s_fu['recall@5']:.0%} | MRR {s_fu['mrr']:.2f} (on {s_fu['n']})")
    for r in followups:
        print(f"  rank={r['rank']} | {r['question'][:45]!r} -> searched: {r['rewritten_query']!r}")

if args.full:
    no_exp = [r for r in rows if not r["has_expected"]]
    wrong_ref = [r for r in rows if r["has_expected"] and r["refused"]]
    print(f"\nCorrect refusals (out-of-scope/ambiguous): "
          f"{sum(r['refused'] for r in no_exp)}/{len(no_exp)}")
    print(f"Wrong refusals (answerable questions): {len(wrong_ref)}")
    clar = [r for r in rows if r.get("clarified")]
    print(f"Clarifying questions asked: {len(clar)} "
          f"({sum(r['category'] == 'ambiguous' for r in clar)} on ambiguous questions)")

print("\n--- Failures ---")
for r in rows:
    if r["has_expected"] and r["rank"] is None:
        print(f"  RETRIEVAL MISS      [{r['category']}] {r['question'][:70]}")
    elif args.full and r["has_expected"] and r["refused"]:
        print(f"  WRONG REFUSAL       [{r['category']}] {r['question'][:70]}")
    elif args.full and not r["has_expected"] and not r["refused"]:
        print(f"  SHOULD HAVE REFUSED [{r['category']}] {r['question'][:70]}")

out = ROOT / args.out
with open(out, "w", encoding="utf-8") as f:
    json.dump({"config": {"full": args.full, "rerank": core.USE_RERANK, "bm25": core.USE_BM25, "rewrite": core.USE_REWRITE,
                          "decompose": core.USE_DECOMPOSE, "expand": core.USE_EXPANSION,
                          "clarify": core.USE_CLARIFY, "index": core.INDEX_FILE},
               "summary": overall, "results": rows}, f, ensure_ascii=False, indent=2)
print(f"\nSaved {args.out}")