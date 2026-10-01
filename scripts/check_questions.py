# Check data/questions.json before running the evals.
# Usage: uv run python scripts/check_questions.py
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with open(ROOT / "data/questions.json", encoding="utf-8") as f:
    questions = json.load(f)
with open(ROOT / "data/corpus.json", encoding="utf-8") as f:
    pages = {(e["source"], e["page"]) for e in json.load(f)}

REQUIRED = ["question", "expected_answer", "category", "difficulty", "priority"]
NO_ANSWER = {"out-of-scope", "ambiguous", "on_topic_unanswerable"}
problems = 0

for i, q in enumerate(questions, 1):
    label = f"#{i} {q.get('question', '?')[:50]!r}"
    for field in REQUIRED:
        if field not in q:
            print(f"MISSING '{field}'  {label}"); problems += 1
    expected = q.get("expected_chunks") or []
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
