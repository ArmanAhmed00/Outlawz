# Check eval/questions.json before running the evals.
# Usage: uv run python scripts/eval/check_questions.py
import sys, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import QUESTIONS_FILE

with open(ROOT / QUESTIONS_FILE, encoding="utf-8") as f:
    questions = json.load(f)
with open(ROOT / "data/corpus.json", encoding="utf-8") as f:
    pages = {(e["source"], e["page"]) for e in json.load(f)}

REQUIRED = ["question", "expected_answer", "category", "difficulty", "priority"]
NO_ANSWER = {"out-of-scope", "ambiguous", "on_topic_unanswerable", "agent"}
problems = 0

for i, q in enumerate(questions, 1):
    label = f"#{i} {q.get('question', '?')[:50]!r}"
    for field in REQUIRED:
        if field not in q:
            print(f"MISSING '{field}'  {label}"); problems += 1
    expected = q.get("expected_chunks") or []
    if q.get("sub_type") == "on_topic_unanswerable":
        q = {**q, "category": "on_topic_unanswerable"}   # a stress-test sub-type with nothing to retrieve
    if q.get("category") == "agent" and not q.get("expected_tools"):
        print(f"AGENT question without expected_tools  {label}"); problems += 1
    if q.get("category") in NO_ANSWER and expected:
        print(f"SHOULD HAVE NO expected_chunks ({q['category']})  {label}"); problems += 1
    if q.get("category") not in NO_ANSWER and not expected:
        print(f"NO expected_chunks -> not counted in recall  {label}"); problems += 1
    for e in expected:
        for p in (e["page"] if isinstance(e["page"], list) else [e["page"]]):
            if (e["source"], p) not in pages:
                print(f"PAGE NOT IN CORPUS {e['source']} p.{p}  {label}"); problems += 1
    if "history" in q and not (isinstance(q["history"], list) and q["history"]):
        print(f"'history' must be a non-empty list of earlier questions  {label}"); problems += 1

print(f"\n{len(questions)} questions | {problems} problem(s)")
print("Categories:", dict(Counter(q.get("category") for q in questions)))
print("Follow-ups (with history):", sum(1 for q in questions if q.get("history")))
print("Priority:", sum(1 for q in questions if q.get("priority")))

# ---- Assignment 1 coverage (follow-up and agent questions don't count) ----
base = [q for q in questions if not q.get("history") and q.get("category") != "agent"]
cross_types = {q.get("sub_type") for q in base if q.get("category") == "cross-reference"} - {None}
stress_types = {q.get("sub_type") for q in base if q.get("category") == "stress-test"} - {None}
print(f"\nAssignment 1: {len(base)} questions (need 40-50)")
print(f"  cross-reference sub-types: {len(cross_types)}/5 needed {sorted(cross_types)}")
print(f"  stress-test sub-types:     {len(stress_types)}/8 needed")
missing = {"adjacent_chunks", "same_document", "different_documents", "repeated",
           "contradictory", "summary_vs_detail"} - cross_types
if len(cross_types) < 5:
    print(f"  -> add a cross-reference question of type: {sorted(missing)}")
