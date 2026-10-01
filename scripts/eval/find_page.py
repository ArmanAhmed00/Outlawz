# Find which (source, page) contains a phrase, to fill "expected_chunks" in questions.json.
# Usage: uv run python scripts/eval/find_page.py "Article 19" "logs"
#        (every phrase must appear on the page, case-insensitive)
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
phrases = [p.lower() for p in sys.argv[1:]]
if not phrases:
    sys.exit('Usage: python scripts/eval/find_page.py "phrase one" ["phrase two" ...]')

with open(ROOT / "data/corpus.json", encoding="utf-8") as f:
    corpus = json.load(f)

hits = 0
for entry in corpus:
    text = entry["text"].lower()
    if all(p in text for p in phrases):
        hits += 1
        pos = text.find(phrases[0])
        snippet = entry["text"][max(0, pos - 60): pos + 140].replace("\n", " ")
        print(f'{{"source": "{entry["source"]}", "page": {entry["page"]}}}')
        print(f"    ...{snippet}...\n")
print(f"{hits} page(s) found")
