# Markdown table of every failure in an eval run, to paste into scripts/FAILURE_LOG.md.
# Usage: uv run python scripts/eval/failure_report.py [eval/results/eval_results.json]
#        (refusal failures only appear for a --full run)
import sys, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import RESULTS_DIR

path = sys.argv[1] if len(sys.argv) > 1 else f"{RESULTS_DIR}/eval_results.json"
with open(ROOT / path, encoding="utf-8") as f:
    data = json.load(f)
rows = data["results"]
full = data["config"].get("full", False)


def failure_type(r):
    """RETRIEVAL MISS / WRONG REFUSAL / SHOULD HAVE REFUSED, or None if it passed."""
    if r["has_expected"] and r["rank"] is None:
        return "RETRIEVAL MISS"
    if full and r["has_expected"] and r["refused"]:
        return "WRONG REFUSAL"
    if full and not r["has_expected"] and not r["refused"]:
        return "SHOULD HAVE REFUSED"
    return None


failures = [(failure_type(r), r) for r in rows if failure_type(r)]

print(f"<!-- {path} ({'full' if full else 'retrieval only'}), {len(failures)} failures -->")
print("| Question | Category | Retrieval OK? | Rank | Problem | Fix applied | Fixed? |")
print("|---|---|:---:|:---:|---|---|:---:|")
for kind, r in failures:
    ok = "-" if not r["has_expected"] else ("yes" if r["rank"] else "no")
    question = r["question"].replace("|", "\\|")
    print(f"| {question} | {r['category']} | {ok} | {r['rank'] or '-'} | {kind} |  |  |")

print()
for kind, n in Counter(kind for kind, _ in failures).items():
    print(f"{kind}: {n}")
if not full:
    print("(retrieval-only results: run eval_runner.py --full to also see refusal failures)")
