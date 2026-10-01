# Compare 2+ eval runs: ablation table + questions that got better / worse by rank.
# Usage: uv run python scripts/eval/compare_runs.py eval/results/eval_t1_base.json eval/results/eval_t1_article.json
#        (refusals are compared only when both runs are --full)
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.eval.metrics import summarize

paths = sys.argv[1:]
if len(paths) < 2:
    sys.exit("Usage: python scripts/eval/compare_runs.py RUN1.json RUN2.json [RUN3.json ...]")

runs = []
for p in paths:
    with open(ROOT / p, encoding="utf-8") as f:
        runs.append((Path(p).stem, json.load(f)))

# ---------------- Ablation table ----------------
print(f"{'run':28} {'n':>3} {'R@1':>6} {'R@3':>6} {'R@5':>6} {'MRR':>6} {'lat(s)':>7}")
for name, run in runs:
    s = summarize(run["results"])
    print(f"{name:28} {s['n']:>3} {s['recall@1']:>6.0%} {s['recall@3']:>6.0%} "
          f"{s['recall@5']:>6.0%} {s['mrr']:>6.2f} {s['latency']:>7.2f}")


def rank_key(rank):
    """Missed (None) counts as worse than any rank."""
    return rank if rank is not None else 99


# ---------------- Per question, each run vs the previous one ----------------
for (name_a, a), (name_b, b) in zip(runs, runs[1:]):
    before = {r["question"]: r for r in a["results"] if r["has_expected"]}
    after = {r["question"]: r for r in b["results"] if r["has_expected"]}
    common = [q for q in after if q in before]
    better = [q for q in common if rank_key(after[q]["rank"]) < rank_key(before[q]["rank"])]
    worse = [q for q in common if rank_key(after[q]["rank"]) > rank_key(before[q]["rank"])]

    print(f"\n--- {name_a} -> {name_b} ({len(common)} questions in both) ---")
    print(f"Better ({len(better)}):")
    for q in better:
        print(f"  rank {before[q]['rank']} -> {after[q]['rank']} | {q[:70]}")
    print(f"Worse ({len(worse)}):")
    for q in worse:
        tag = "  BROKE" if after[q]["rank"] is None else ""
        print(f"  rank {before[q]['rank']} -> {after[q]['rank']} | {q[:70]}{tag}")

    if a["config"].get("full") and b["config"].get("full"):
        ref_a = {r["question"]: r["refused"] for r in a["results"]}
        ref_b = {r["question"]: r["refused"] for r in b["results"]}
        changed = [q for q in ref_b if q in ref_a and ref_a[q] != ref_b[q]]
        print(f"Refusal changed ({len(changed)}):")
        for q in changed:
            print(f"  {'answered -> refused' if ref_b[q] else 'refused -> answered'} | {q[:70]}")
