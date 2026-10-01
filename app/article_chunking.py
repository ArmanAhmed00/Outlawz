"""Article-aware chunking: cut the legal texts at "Article N" headings, not every 500 chars.

Every chunk starts with a header like "GDPR Article 5 - Principles relating to processing
of personal data", so the article number is in the text (helps BM25 and embeddings).
Long articles are split into pieces of ~ARTICLE_CHUNK_SIZE chars at line boundaries,
each piece keeping the header. NIST has no articles: it is grouped by size only.
"""
import re
from app.core import ARTICLE_CHUNK_SIZE, ARTICLE_OVERLAP

DOC_NAMES = {
    "CELEX_02016R0679-20160504_EN_TXT.pdf": "GDPR",
    "OJ_L_202401689_EN_TXT.pdf": "EU AI Act",
    "NIST.AI.100-1.pdf": "NIST AI RMF",
}

HEADING = re.compile(r"^\s*Article\s+(\d+[a-z]?)\s*$")
NOISE = re.compile(                      # repeated page headers / footers / markers
    r"^\s*(\d+/\d+|EN|OJ L, [\d.]+|ELI: \S+|▼[A-Z]\d*|NIST AI 100-1|AI RMF 1\.0|Page \d+"
    r"|\d{5}R\d{4} — EN — .*)\s*$"
)


def _lines_with_pages(entries):
    """All lines of one document, in order, with the page each line comes from."""
    out = []
    for e in sorted(entries, key=lambda e: e["page"]):
        for line in e["text"].split("\n"):
            if line.strip() and not NOISE.match(line):
                out.append((line.strip(), e["page"]))
    return out


def _sections(doc, lines):
    """Split a document into (header, article, [(line, page), ...]) at Article headings."""
    sections, header, article, body = [], f"{doc} (introduction / recitals)", None, []
    i = 0
    while i < len(lines):
        m = HEADING.match(lines[i][0])
        if m and i + 1 < len(lines):
            if body:
                sections.append((header, article, body))
            article = f"Article {m.group(1)}"
            title = lines[i + 1][0]
            header, body = f"{doc} {article} - {title}", []
            i += 2
            continue
        body.append(lines[i])
        i += 1
    if body:
        sections.append((header, article, body))
    return sections


def _split(body, size, overlap):
    """Group lines into pieces of ~size chars; the next piece repeats ~overlap chars."""
    pieces, current = [], []
    for line, page in body:
        if current and sum(len(l) + 1 for l, _ in current) + len(line) > size:
            pieces.append(current)
            keep, kept = [], 0
            for l, p in reversed(current):          # carry the last lines as overlap
                if kept + len(l) > overlap:
                    break
                keep.insert(0, (l, p))
                kept += len(l) + 1
            current = keep
        current.append((line, page))
    if current:
        pieces.append(current)
    return pieces


def chunk_corpus_by_article(corpus, size=ARTICLE_CHUNK_SIZE, overlap=ARTICLE_OVERLAP):
    """Same output format as chunk_corpus(), plus 'article' and 'pages' fields."""
    chunks = []
    for source in sorted({e["source"] for e in corpus}):
        doc = DOC_NAMES.get(source, source)
        lines = _lines_with_pages([e for e in corpus if e["source"] == source])
        for header, article, body in _sections(doc, lines):
            for piece in _split(body, size, overlap):
                text = header + "\n" + "\n".join(l for l, _ in piece)
                pages = sorted({p for _, p in piece})
                chunks.append({
                    "source": source,
                    "page": pages[0],
                    "pages": pages,
                    "article": article,
                    "char_count": len(text),
                    "text": text,
                })
    return chunks
