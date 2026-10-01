import sys
sys.path.insert(0, ".")

import faiss, json
from agent.loop import run_agent
from agent.dispatcher import build_tool_functions
from agent.tools.schemas import calculator_schema, search_corpus_schema, quote_exact_schema
from app.core import get_total_cost

index = faiss.read_index("data/my_index.faiss")
chunks = json.load(open("data/chunks.json"))

tools = [calculator_schema, search_corpus_schema, quote_exact_schema]
tool_functions = build_tool_functions(index, chunks)

query = " ".join(sys.argv[1:]) or input("Question : ")
answer = run_agent(query, tools, tool_functions)

print("\n=== Response ===")
print(answer)
print(f"Total cost: ${get_total_cost():.4f}")