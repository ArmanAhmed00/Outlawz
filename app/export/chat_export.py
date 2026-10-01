"""Export a chat (questions, answers, sources) as a formatted PDF or Word file.

Uses only PyMuPDF (already in the project). The Word file is HTML saved as .doc,
which Word, LibreOffice and Google Docs open with the formatting kept.
"""
import io
import re
import html
from datetime import datetime

import pymupdf

CSS = """
body, p, li { font-family: Arial, Helvetica, sans-serif; font-size: 10pt; color: #222222; }
h1    { font-family: Arial, Helvetica, sans-serif; font-size: 20pt; color: #1F3A5F; margin-bottom: 2pt; }
h2    { font-family: Arial, Helvetica, sans-serif; font-size: 12pt; color: #1F3A5F; margin-top: 14pt; margin-bottom: 4pt; }
.meta { font-size: 8pt; color: #777777; }
.q    { font-weight: bold; color: #1F3A5F; margin-top: 6pt; }
.src  { font-size: 8pt; color: #555555; margin-top: 4pt; }
li    { margin-bottom: 2pt; }
"""


def _inline(text):
    """Escape HTML, then turn **bold** and `code` into tags."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def markdown_to_html(md):
    """Small Markdown -> HTML (headings, bullet / numbered lists, bold, paragraphs)."""
    out, list_tag = [], None
    for line in md.splitlines():
        s = line.strip()
        bullet = re.match(r"^[-*•]\s+(.*)", s)
        number = re.match(r"^\d+[.)]\s+(.*)", s)
        tag = "ul" if bullet else "ol" if number else None
        if list_tag and tag != list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None
        if tag:
            if not list_tag:
                out.append(f"<{tag}>")
                list_tag = tag
            out.append(f"<li>{_inline((bullet or number).group(1))}</li>")
        elif s.startswith("#"):
            out.append(f"<p><b>{_inline(s.lstrip('#').strip())}</b></p>")
        elif s:
            out.append(f"<p>{_inline(s)}</p>")
    if list_tag:
        out.append(f"</{list_tag}>")
    return "\n".join(out)


def chat_to_html(turns, title="Outlawz – Chat export"):
    """turns: list of {"question": str, "answer": str, "sources": [str, ...]}."""
    parts = [f"<h1>{html.escape(title)}</h1>",
             f"<p class='meta'>Exported on {datetime.now():%d %B %Y, %H:%M} · "
             f"{len(turns)} questions · Corpus: GDPR, EU AI Act, NIST AI RMF</p>"]
    for i, t in enumerate(turns, 1):
        parts.append(f"<h2>Question {i}</h2>")
        parts.append(f"<p class='q'>{_inline(t['question'])}</p>")
        parts.append(markdown_to_html(t["answer"]))
        if t.get("sources"):
            parts.append(f"<p class='src'><b>Sources:</b> {html.escape('; '.join(t['sources']))}</p>")
    return "\n".join(parts)


def chat_to_pdf(turns):
    """PDF bytes, A4, multi-page (PyMuPDF Story lays the HTML out page by page)."""
    story = pymupdf.Story(html=chat_to_html(turns), user_css=CSS)
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    page = pymupdf.paper_rect("a4")
    area = page + (50, 50, -50, -50)          # 50 pt margins
    more = True
    while more:
        device = writer.begin_page(page)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()
    return buffer.getvalue()


def chat_to_doc(turns):
    """Word-compatible .doc bytes (HTML with Office headers)."""
    page = ("<html xmlns:o='urn:schemas-microsoft-com:office:office' "
            "xmlns:w='urn:schemas-microsoft-com:office:word'>"
            f"<head><meta charset='utf-8'><style>{CSS}</style></head>"
            f"<body>{chat_to_html(turns)}</body></html>")
    return page.encode("utf-8")
