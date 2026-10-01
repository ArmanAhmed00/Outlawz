# Usage: uv run python scripts/eval/threshold_sweep.py [eval/results/eval_results.json]
# Re-tune RERANK_THRESHOLD on a retrieval-only run made with the current index.
import sys, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import RERANK_THRESHOLD, RESULTS_DIR

path = sys.argv[1] if len(sys.argv) > 1 else f"{RESULTS_DIR}/eval_results.json"
with open(ROOT / path, encoding="utf-8") as f:
    rows = json.load(f)["results"]

answerable = [r for r in rows if r["has_expected"]]
out_of_scope = [r for r in rows if r["category"] == "out-of-scope"]
should_refuse = [r for r in rows if not r["has_expected"]]   # out-of-scope, ambiguous, unanswerable
print(f"{path}: {len(answerable)} answerable, {len(out_of_scope)} out-of-scope, "
      f"{len(should_refuse)} should-refuse in total\n")

# ---- Sweep -8 .. 0, step 0.25 ----
candidates = [-8 + i * 0.25 for i in range(33)]
scores = {}
print(f"{'threshold':>9} | {'wrong refusals':>14} | {'out-of-scope let through':>24} | {'all should-refuse caught':>24}")
for t in candidates:
    wrong = sum(r["top_rerank"] < t for r in answerable)
    leak = sum(r["top_rerank"] >= t for r in out_of_scope)
    caught = sum(r["top_rerank"] < t for r in should_refuse)
    scores[t] = (wrong, leak)
    mark = "  <- current" if t == RERANK_THRESHOLD else ""
    print(f"{t:>9.2f} | {wrong:>7}/{len(answerable):<6} | {leak:>12}/{len(out_of_scope):<11} | "
          f"{caught:>12}/{len(should_refuse):<11}{mark}")

# best = fewest wrong refusals, then fewest out-of-scope leaks; the middle of the tied range keeps
# the most margin on both sides (the LLM still refuses the on-topic unanswerable ones)
best_score = min(scores.values())
tied = [t for t in candidates if scores[t] == best_score]
suggested = tied[len(tied) // 2]
print(f"\nBest: {best_score[0]} wrong refusals, {best_score[1]} out-of-scope let through "
      f"for every threshold in [{tied[0]:.2f}, {tied[-1]:.2f}]")
print(f"Suggested RERANK_THRESHOLD = {suggested:.2f}  (middle of that range; current: {RERANK_THRESHOLD})")

print("\nAll questions, lowest reranker score first:")
for r in sorted(rows, key=lambda r: r["top_rerank"]):
    tag = "answerable" if r["has_expected"] else "REFUSE    "
    print(f"{r['top_rerank']:+7.2f}  {tag}  [{r['category']}] {r['question'][:60]}")

# ---- Breakdown at the threshold currently set in app/core.py ----
groups = defaultdict(lambda: [0, 0])
for r in rows:
    g = groups["on_topic_unanswerable" if r.get("sub_type") == "on_topic_unanswerable" else r["category"]]
    g[0] += r["top_rerank"] < RERANK_THRESHOLD
    g[1] += 1
print(f"\nAt the current threshold ({RERANK_THRESHOLD}), refused per category:")
for cat, (refused, n) in groups.items():
    goal = "should refuse" if cat in {"out-of-scope", "ambiguous", "on_topic_unanswerable"} else "should answer"
    print(f"  {cat:22} {refused}/{n} refused   ({goal})")
