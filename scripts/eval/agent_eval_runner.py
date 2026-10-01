# Agent eval: agent questions (category "agent") + the 5 priority questions, run through the agent.
# Usage: uv run python scripts/eval/agent_eval_runner.py            (agent only)
#        uv run python scripts/eval/agent_eval_runner.py --rag      (+ same questions through the RAG -> agent vs RAG)
# send_message is never really sent here: fake_decline() plays the person saying no.
import sys, json, time, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import RESULTS_DIR

parser = argparse.ArgumentParser()
parser.add_argument("--rag", action="store_true", help="also answer with the RAG pipeline (agent vs RAG)")
parser.add_argument("--out", default=f"{RESULTS_DIR}/agent_eval_results.json")
args = parser.parse_args()

import app.core as core
core.INJECTION_TEST = False

import faiss
import agent.model
import app.embeddings
from agent.loop import run_agent
from agent.dispatcher import build_tool_functions
from agent.tools.schemas import ALL_TOOLS
from agent.tools import messaging
from app.generation.generate_answer import answer_question

# ---- count every chat-model call (agent client + RAG client) ----
CALLS = {"n": 0}
for client in {id(agent.model.client): agent.model.client, id(app.embeddings.client): app.embeddings.client}.values():
    original = client.chat.completions.create

    def counted(*a, _orig=original, **kw):
        CALLS["n"] += 1
        return _orig(*a, **kw)
    client.chat.completions.create = counted

index = faiss.read_index(str(ROOT / core.INDEX_FILE))
with open(ROOT / core.CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)
with open(ROOT / core.QUESTIONS_FILE, encoding="utf-8") as f:
    all_q = json.load(f)
questions = [q for q in all_q if q["category"] == "agent"] + \
            [q for q in all_q if q.get("priority") and q["category"] != "agent"]
if not any(q["category"] == "agent" for q in questions):
    print("No agent questions yet: add questions with \"category\": \"agent\" to eval/questions.json")

tool_functions = build_tool_functions(index, chunks)
send_log = []
rows = []
for i, q in enumerate(questions, 1):
    history = [{"role": "user", "content": h} for h in q.get("history", [])]
    messaging.PROPOSALS.clear()
    CALLS["n"] = 0
    t0 = time.perf_counter()
    out = run_agent(q["question"], ALL_TOOLS, tool_functions, verbose=False, trace=True, history=history)
    latency = time.perf_counter() - t0
    declined = messaging.fake_decline(send_log)
    used = [t["tool"] for t in out["trace"]]
    expected = q.get("expected_tools") or []
    row = {
        "question": q["question"],
        "group": q.get("sub_type") if q["category"] == "agent" else "priority",
        "priority": bool(q.get("priority")),
        "expected_answer": q.get("expected_answer"),
        "answer": out["answer"],
        "tools_used": used,
        "expected_tools": expected,
        "tools_ok": set(expected) <= set(used) if expected else (not used if expected == [] and "expected_tools" in q else None),
        "tool_calls": len(used),
        "model_calls": CALLS["n"],
        "repeated_calls": sum("You already called" in t["result"] for t in out["trace"]),
        "hit_step_cap": out["answer"].startswith("Stopped"),
        "searches": used.count("search_corpus"),
        "proposed_send": bool(declined),
        "latency": round(latency, 2),
        "correct": None,          # fill in by hand: true / false
    }
    if args.rag:
        CALLS["n"] = 0
        t0 = time.perf_counter()
        rag_answer, _ = answer_question(q["question"], index, chunks, history=history)
        row.update({"rag_answer": rag_answer, "rag_model_calls": CALLS["n"],
                    "rag_latency": round(time.perf_counter() - t0, 2), "rag_correct": None})
    rows.append(row)
    print(f"[{i:2}/{len(questions)}] {row['group']:<22} tools={used} ok={row['tools_ok']} "
          f"calls={row['model_calls']} {row['latency']}s | {q['question'][:50]}")


def avg(rs, key):
    vals = [r[key] for r in rs if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else 0


def report(title, rs):
    tool_rows = [r for r in rs if r["tools_ok"] is not None]
    tool_ok = f"{sum(r['tools_ok'] for r in tool_rows)}/{len(tool_rows)}" if tool_rows else "-"
    print(f"{title:24} n={len(rs):<3} tools ok {tool_ok:<6} steps {avg(rs, 'tool_calls'):.1f}  "
          f"model calls {avg(rs, 'model_calls'):.1f}  repeated {sum(r['repeated_calls'] for r in rs)}  "
          f"step cap {sum(r['hit_step_cap'] for r in rs)}  latency {avg(rs, 'latency'):.1f}s")


print("\n===== AGENT =====")
report("overall", rows)
report("priority questions", [r for r in rows if r["priority"]])
groups = defaultdict(list)
for r in rows:
    groups[r["group"]].append(r)
for name, rs in groups.items():
    report(f"  {name}", rs)
oos = [r for r in rows if r["group"] == "out_of_scope"]
if oos:
    print(f"Out of scope stopped cleanly (<= {core.MAX_FAILED_SEARCHES} searches): "
          f"{sum(r['searches'] <= core.MAX_FAILED_SEARCHES for r in oos)}/{len(oos)}")
print(f"send_message proposals (all declined by the fake approver): {len(send_log)}")

if args.rag:
    print("\n===== AGENT vs RAG (correctness: fill 'correct' / 'rag_correct' by hand in the JSON) =====")
    print(f"{'':10} {'model calls':>12} {'latency(s)':>11}")
    print(f"{'agent':10} {avg(rows, 'model_calls'):>12.1f} {avg(rows, 'latency'):>11.2f}")
    print(f"{'RAG':10} {avg(rows, 'rag_model_calls'):>12.1f} {avg(rows, 'rag_latency'):>11.2f}")

with open(ROOT / args.out, "w", encoding="utf-8") as f:
    json.dump({"rag": args.rag, "results": rows, "send_log": send_log}, f, ensure_ascii=False, indent=2)
print(f"\nSaved {args.out}")
