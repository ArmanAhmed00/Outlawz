# Extraction Report

## Corpus overview

- 3 source PDFs, 270 pages total, ~899,600 characters extracted, avg ~3,331 characters/page
- 0 empty or near-empty (<50 char) entries — every page produced extractable text
- No scanned or image-only pages encountered — all 3 sources are digitally-produced PDFs with selectable text throughout, so no OCR concerns for this corpus

## Report 

```
source files: 3
total entries: 270
total characters: 899618
avg characters/entry: 3331
near-empty entries (<50 chars): 0
```

## Cleaning

**At extraction (`scripts/ingest/extract.py`):** only light cleaning. Each line is stripped of
leading/trailing whitespace and empty lines are dropped. Pages under 50 characters are kept but
counted (there were none). Headers and footers are **not** removed here, so `data/corpus.json`
keeps the page text as PyMuPDF returns it.

**At article chunking (`app/article_chunking.py`, used by the article index):** every line that
matches the `NOISE` regex is dropped before chunking: 883 lines across the 270 pages.

| Removed line | Example | Where it comes from | Lines |
|---|---|---|:---:|
| Language tag | `EN` | AI Act page header | 144 |
| ELI link | `ELI: http://data.europa.eu/eli/reg/2024/1689/oj` | AI Act page footer | 144 |
| Official Journal reference | `OJ L, 12.7.2024` | AI Act page header | 143 |
| Page numbers | `12/144`, `Page 12` | AI Act / NIST footers | 188 |
| Consolidation markers `▼` | `▼B`, `▼C1` | GDPR consolidated text (marks original text / corrigenda) | 98 |
| Consolidated version header | `02016R0679 — EN — 04.05.2016 — 000.002 — 2` | GDPR page header | 78 |
| NIST running header | `NIST AI 100-1`, `AI RMF 1.0` | NIST page header | 88 |

One false positive: a GDPR line containing only `2016/679` (the regulation number) matches the
`\d+/\d+` page-number pattern and is dropped too.

Lines are then grouped by `Article N` headings, and each chunk starts with a header such as
`GDPR Article 5 - Principles relating to processing of personal data`. The original fixed-size
chunks (`app/chunking.py`) do no cleaning: they cut the raw page text every 500 characters, so
these headers and footers end up inside the chunks.
