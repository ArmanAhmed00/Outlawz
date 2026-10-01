# Usage: uv run python scripts/chat_rag.py   (empty line or 'quit' to exit)
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import faiss
from app.core import INDEX_FILE, CHUNKS_FILE
from app.generate_answer import answer_question
from app.injection import add_injection_chunk

index = faiss.read_index(str(ROOT / INDEX_FILE))
with open(ROOT / CHUNKS_FILE, encoding="utf-8") as f:
    chunks = json.load(f)

index, chunks = add_injection_chunk(index, chunks)  # no-op unless INJECTION_TEST

history = []
while True:
    q = input("\nYou: ").strip()
    if q.lower() in {"", "quit", "exit"}:
        break
    answer, sources = answer_question(q, index, chunks, history=history)
    print(f"\nBot: {answer}")
    for s in sources:
        print(f"  - {s['source']} p.{s['page']}")
    history += [{"role": "user", "content": q}, {"role": "assistant", "content": answer}]
