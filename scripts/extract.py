# scripts/extract.py
import json
from pathlib import Path
import pymupdf as fitz  # PyMuPDF

SOURCES = Path("data/sources")
MIN_CHARS = 50

def clean(text: str) -> str:
    # collapse whitespace; add your own header/footer removal
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)

def extract_pdf(path):
    doc = fitz.open(path)
    for i, page in enumerate(doc, start=1): #type: ignore

        yield i, clean(page.get_text())

def extract_text_file(path):
    yield 1, clean(path.read_text(encoding="utf-8"))

def main():
    entries, near_empty = [], 0
    for path in sorted(SOURCES.iterdir()):
        ext = path.suffix.lower()
        if ext == ".pdf":
            pages = extract_pdf(path)
        elif ext in {".txt", ".md"}:
            pages = extract_text_file(path)
        else:
            continue  # add .html handling with BeautifulSoup if needed
        for page, text in pages:
            if len(text) < MIN_CHARS:
                near_empty += 1        # keep it, but count it
            entries.append({
                "source": path.name,
                "page": page,
                "char_count": len(text),
                "text": text,
            })

    Path("data/corpus.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/sample.json").write_text(
        json.dumps(entries[:10], ensure_ascii=False, indent=2), encoding="utf-8")

    chars = sum(e["char_count"] for e in entries)
    files = len({e["source"] for e in entries})
    print(f"source files: {files}")
    print(f"total entries: {len(entries)}")
    print(f"total characters: {chars}")
    print(f"avg characters/entry: {chars // max(len(entries), 1)}")
    print(f"near-empty entries (<{MIN_CHARS} chars): {near_empty}")

if __name__ == "__main__":
    main()