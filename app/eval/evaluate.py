# app/eval/evaluate.py
# Run with: python app/eval/evaluate.py
# Based on "Running Your Eval Set" + Section 9 (LLM-as-judge) of the code reference.

import sys, json
sys.path.insert(0, ".")

import faiss
from app.core import REFUSAL, INDEX_FILE, CHUNKS_FILE
from app.search.retrieval import retrieve
from app.generation.generate_answer import safe_chat, answer_question

USE_JUDGE = False  # set True to also check faithfulness (costs a bit more)


# ---------------- Section 9: LLM-as-Judge ----------------
def judge_faithfulness(question, answer, context):
    response = safe_chat([
        {"role": "system", "content": (
            "You are an evaluation judge. Given a question, an answer, "
            "and the context that was provided, determine if the answer "
            "is faithful to the context. Score: 'faithful' if every claim "
            "in the answer is supported by the context, 'unfaithful' if "
            "the answer contains information not in the context."
        )},
        {"role": "user", "content": (
            f"Question: {question}\n\n"
            f"Context: {context}\n\n"
            f"Answer: {answer}\n\n"
            f"Is the answer faithful to the context?"
        )}
    ], max_tokens=100)
    return response.choices[0].message.content if response else "error"


# Load eval set
with open("data/questions.json", encoding="utf-8") as f:
    questions = json.load(f)

# Load index and chunks
index = faiss.read_index(INDEX_FILE)
with open(CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)

hits, total_with_chunks = 0, 0
refusals_ok, total_out_of_scope = 0, 0
results_log = []

# Run all questions
for q in questions:
    results = retrieve(q["question"], index, chunks, k=5)
    answer, sources = answer_question(q["question"], index, chunks)

    # Retrieval check: did we retrieve at least one expected (source, page)?
    hit = None
    if q.get("expected_chunks"):
        total_with_chunks += 1
        retrieved = {(r["source"], r["page"]) for r in results}
        expected = set()
        for e in q["expected_chunks"]:
            pages = e["page"] if isinstance(e["page"], list) else [e["page"]]
            expected.update((e["source"], p) for p in pages)
        hit = len(expected & retrieved) > 0
        hits += hit

    # Out-of-scope check: did the system refuse?
    refused = REFUSAL.lower().rstrip(".") in answer.lower()#type: ignore
    if q["category"] == "out-of-scope":
        total_out_of_scope += 1
        refusals_ok += refused

    print(f"Q: {q['question']}")
    print(f"A: {answer}")
    print(f"Expected: {q['expected_answer']}")
    print(f"Category: {q['category']} | best score: {results[0]['score']:.3f} | retrieval hit: {hit}")

    if USE_JUDGE and sources:
        context = "\n\n".join(r["text"] for r in sources)
        print(f"Judge: {judge_faithfulness(q['question'], answer, context)}")
    print("---")

    results_log.append({"question": q["question"], "category": q["category"], "answer": answer,
                        "expected": q["expected_answer"], "hit": hit, "refused": refused,
                        "best_score": results[0]["score"]})

# Summary
print("\n===== SUMMARY =====")
if total_with_chunks:
    print(f"Retrieval hit rate: {hits}/{total_with_chunks} = {hits / total_with_chunks:.0%}")
if total_out_of_scope:
    print(f"Correct refusals (out-of-scope): {refusals_ok}/{total_out_of_scope}")

with open("data/eval_results.json", "w", encoding="utf-8") as f:
    json.dump(results_log, f, ensure_ascii=False, indent=2)
print("Saved data/eval_results.json")