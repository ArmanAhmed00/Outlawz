import sys
sys.path.insert(0, ".")

import faiss, json
from agent.loop import run_agent
from agent.dispatcher import build_tool_functions
from agent.tools.schemas import calculator_schema, search_corpus_schema, quote_exact_schema

index = faiss.read_index("data/my_index.faiss")
chunks = json.load(open("data/chunks.json"))
tools = [calculator_schema, search_corpus_schema, quote_exact_schema]
tool_functions = build_tool_functions(index, chunks)


questions = [
    "What does the GDPR say about the right to erasure?",
    "What are the prohibited AI practices under Article 5 of the AI Act?",

    "What is 15% of 10000, plus 250?",
    "If a fine is 20 million euros, what is 4% of 500 million? Which is higher?",

    "What are the obligations for high-risk AI systems, and how many articles does the AI Act have about them roughly?",
    "What is the maximum fine percentage under GDPR Article 83, and what would that be for a company with 50 million euros in revenue?",

    "What is the weather in Paris?",
    "Who won the 2018 football world cup?",

    "What does Article 500 of the GDPR say?",
    "What does the AI Act say about cryptocurrency regulation?",

]

def print_result(question, out):
    print("\n" + "=" * 80)
    print(f"Q: {question}")
    print("=" * 80)
    print(f"Steps used: {out['steps']}\n")

    if not out["trace"]:
        print("(no tool calls)")
    else:
        for i, t in enumerate(out["trace"], 1):
            result_preview = t["result"].replace("\n", " ").strip()
            if len(result_preview) > 100:
                result_preview = result_preview[:100] + "..."
            print(f"  [{i}] {t['tool']}({t['arguments']})")
            print(f"      -> {result_preview}")

    print(f"\nAnswer:\n{out['answer']}")


for q in questions:
    out = run_agent(q, tools, tool_functions, verbose=False, trace=True)
    print_result(q, out)

print("\n" + "=" * 80)
print(f"{len(questions)} questions evaluated")