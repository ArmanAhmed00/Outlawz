"""Read-only lookup tools over the article-aware chunks (data/chunks_article.json).

get_article(regulation, article): full text of one article, e.g. GDPR Article 5.
define_term(term): official definition from GDPR Art. 4 or EU AI Act Art. 3.
Search alone does these badly: it returns 500-char pieces of an article, or passages that
merely USE a term instead of defining it (see scripts/FAILURE_LOG.md).
"""
import re
import json
from pathlib import Path
import app.core as core

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "gdpr": "CELEX_02016R0679-20160504_EN_TXT.pdf",
    "ai act": "OJ_L_202401689_EN_TXT.pdf",
    "eu ai act": "OJ_L_202401689_EN_TXT.pdf",
}
NAMES = {"CELEX_02016R0679-20160504_EN_TXT.pdf": "GDPR", "OJ_L_202401689_EN_TXT.pdf": "EU AI Act"}
DEFINITION_ARTICLES = [("CELEX_02016R0679-20160504_EN_TXT.pdf", "Article 4"),
                       ("OJ_L_202401689_EN_TXT.pdf", "Article 3")]
MAX_CHARS = 6000          # keep tool results short: every step resends them

_chunks = None
_definitions = None


def _article_chunks():
    global _chunks
    if _chunks is None:
        with open(ROOT / core.ARTICLE_CHUNKS_FILE, encoding="utf-8") as f:
            _chunks = json.load(f)
    return _chunks


def _article_text(source, article):
    """Body of one article (chunk headers and overlapping lines removed) + its pages."""
    lines, pages, title = [], set(), None
    for c in _article_chunks():
        if c["source"] == source and c.get("article") == article:
            header, *body = c["text"].split("\n")
            title = title or header
            pages.update(c.get("pages", [c["page"]]))
            for line in body:
                if line not in lines[-5:]:          # skip the overlap repeated by the next chunk
                    lines.append(line)
    return title, " ".join(lines), sorted(pages)


def get_article(regulation: str, article: str) -> str:
    source = SOURCES.get(regulation.strip().lower())
    if not source:
        return "Unknown regulation. Use 'GDPR' or 'EU AI Act' (NIST AI RMF has no articles)."
    number = re.sub(r"(?i)^\s*art(icle)?\.?\s*", "", str(article)).strip()
    number = re.match(r"\d+[a-z]?", number)
    if not number:
        return "Give the article number, e.g. '5' or 'Article 5' (not a paragraph like 5(1))."
    title, text, pages = _article_text(source, f"Article {number.group(0)}")
    if not text:
        return f"No Article {number.group(0)} found in the {NAMES[source]}."
    cut = " [...truncated]" if len(text) > MAX_CHARS else ""
    return f"{title} (source: {source}, pages {pages})\n{text[:MAX_CHARS]}{cut}"


def _load_definitions():
    """{(term, regulation): (regulation, article, number, term, definition, source, pages)}."""
    global _definitions
    if _definitions is None:
        _definitions = {}
        for source, article in DEFINITION_ARTICLES:
            _, text, pages = _article_text(source, article)
            text = re.sub(r"\s+", " ", text).replace("\xad ", "").replace("\xad", "")
            pattern = r"\(\s*(\d+)\s*\)\s*[‘']([^’']+)[’']\s*means\s*(.+?)(?=\(\s*\d+\s*\)\s*[‘']|$)"
            for num, term, definition in re.findall(pattern, text):
                key = (term.lower(), NAMES[source])
                if key not in _definitions:
                    _definitions[key] = (NAMES[source], article, num, term, definition.strip(), source, pages)
    return _definitions


def define_term(term: str, regulation: str = "") -> str:
    defs = _load_definitions()
    wanted = term.strip().lower().strip("'‘’\"")
    reg = {"gdpr": "GDPR", "ai act": "EU AI Act", "eu ai act": "EU AI Act"}.get(regulation.strip().lower())
    hits = [v for (t, r), v in defs.items() if t == wanted and (not reg or r == reg)]
    if not hits:   # partial match, e.g. 'biometric' -> 'biometric data'
        hits = [v for (t, r), v in defs.items() if wanted in t and (not reg or r == reg)][:3]
    if not hits:
        return (f"No official definition of '{term}' in GDPR Art. 4 or EU AI Act Art. 3. "
                "Use search_corpus instead.")
    return "\n\n".join(f"{r} {a}({n}): '{t}' means {d} (source: {s}, pages {p})"
                       for r, a, n, t, d, s, p in hits)
