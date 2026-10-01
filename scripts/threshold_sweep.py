# Usage: uv run python scripts/threshold_sweep.py [data/eval_results.json]
import sys, json

path = sys.argv[1] if len(sys.argv) > 1 else "data/eval_results.json"
with open(path, encoding="utf-8") as f:
    rows = json.load(f)["results"]

should_refuse = [r for r in rows if not r["has_expected"]]   # out-of-scope, ambiguous, unanswerable
answerable = [r for r in rows if r["has_expected"]]

print(f"{len(should_refuse)} should-refuse questions, {len(answerable)} answerable\n")
print(f"{'threshold':>9} | {'correct refusals':>16} | {'wrong refusals':>14}")
for t in [-9, -8, -7, -6, -5, -4.5, -4, -3, -2, -1, 0, 1, 2]:
    ok = sum(r["top_rerank"] < t for r in should_refuse)
    wrong = sum(r["top_rerank"] < t for r in answerable)
    print(f"{t:>9} | {ok:>9}/{len(should_refuse):<6} | {wrong:>8}/{len(answerable)}")

print("\nAll questions, lowest reranker score first:")
for r in sorted(rows, key=lambda r: r["top_rerank"]):
    tag = "answerable" if r["has_expected"] else "REFUSE    "
    print(f"{r['top_rerank']:+7.2f}  {tag}  [{r['category']}] {r['question'][:60]}")

# ---- Breakdown at the threshold currently set in app/core.py ----
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core import RERANK_THRESHOLD

groups = defaultdict(lambda: [0, 0])
for r in rows:
    g = groups[r["category"]]
    g[0] += r["top_rerank"] < RERANK_THRESHOLD
    g[1] += 1
print(f"\nAt the current threshold ({RERANK_THRESHOLD}), refused per category:")
for cat, (refused, n) in groups.items():
    goal = "should refuse" if cat in {"out-of-scope", "ambiguous", "on_topic_unanswerable"} else "should answer"
    print(f"  {cat:22} {refused}/{n} refused   ({goal})")
