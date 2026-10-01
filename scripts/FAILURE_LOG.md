# Failure log

**How failures are found:** `scripts/eval/eval_runner.py --full` → `scripts/eval/failure_report.py`
(lists every failure) → `scripts/eval/retrieval_checker.py "<question>"` (shows the retrieved
chunks with ✅/❌ against the expected pages) to decide if it is a retrieval or a generation problem.

**Categories:** RETRIEVAL MISS (expected page not in the top 5) · WRONG REFUSAL (page retrieved,
system still refused) · SHOULD HAVE REFUSED (ambiguous / not in the corpus, but answered).

Full run analysed (`eval/results/eval_results.json`, 43 questions, before the follow-up questions were
added): R@1 69%, R@5 81%, MRR 0.74 · 11 failures (6 retrieval miss, 2 wrong refusal,
3 should have refused).

## Failures

| Question | Category | Retrieval OK? | Rank | Problem | Fix applied | Fixed? |
|---|---|:---:|:---:|---|---|:---:|
| What regulation lays down rules ... and repeals Directive 95/46/EC? | factual | ✅ | 2 | Was a miss with vector only: the answer also appears in the AI Act, which outranked the GDPR page | Reranking + BM25 | ✅ |
| How do the lawful grounds for processing standard personal data differ from the conditions for special categories? | cross-reference | ❌ | - | Needs two articles (Art. 6 and Art. 9); found by vector search, lost after reranking (regression) | Open: retrieve more chunks for multi-part questions / query expansion | ❌ |
| How do the rules governing data portability interact with the right to erasure? | cross-reference | ✅ | 1 | Generation: right chunk at rank 1, but the LLM refused because no single chunk covers both articles | Open: prompt allows partial answers combining chunks | ❌ |
| What rules govern data anonymization and user privacy protection in this text? | stress-test | ❌ | - | Vague wording ("in this text"); anonymisation is only mentioned briefly in the recitals | Open: query expansion | ❌ |
| What specific provisions are outlined in Article 2(2)(c)? | stress-test | ❌ | - | Exact reference: BM25 splits "2(2)(c)" into "2", "2", "c", which are too common to help | Open: article-aware chunking / tokenization | ❌ |
| If a non-EU business tracks user habits of people in France ..., do they need parental consent for 14-year-olds? | stress-test | ❌ | - | Two-part question (Art. 3(2) + Art. 8); found by vector search, lost after reranking (regression); then refused by the threshold (score -8.7) | Open: split multi-part questions before retrieval | ❌ |
| What are the six principles relating to processing of personal data listed under Article 5(1)? | stress-test | ✅ | 1 | Generation: the list is cut across two 500-character chunks, so the LLM saw an incomplete list and refused | Open: larger / article-based chunks | ❌ |
| What were the administrative fine limits for data breaches under the 1995 Data Protection Directive? | stress-test | ❌ | - | Not in the corpus: the 1995 Directive is not one of our documents (the GDPR only repeals it). Label issue | Open: relabel as on_topic_unanswerable | ❌ |
| What is the maximum penalty fine for failing to comply with an order by a Supervisory Authority? | stress-test | ❌ | - | Exact provision (Art. 83(6)) not retrieved; the fines article is split over several chunks | Open: article-aware chunking | ❌ |
| Tell me about the requirements. | ambiguous | - | - | On-topic, so the threshold cannot catch it; the LLM guessed (AI Act high-risk requirements) instead of asking which requirements | Open: prompt rule "ask for clarification when the question is vague" | ❌ |
| What are the rules regarding consent? | ambiguous | - | - | Same as above (answered with GDPR consent rules) | Open: same prompt rule | ❌ |
| How does the law deal with exceptions? | ambiguous | - | - | Same as above | Open: same prompt rule | ❌ |

## Regression check

Retrieval-only runs on the same 32 answerable questions. "Broke" = had a rank before, missed after.

| Run | R@1 | R@5 | MRR | Fixed | Broke |
|---|:---:|:---:|:---:|---|---|
| Vector only (`eval/results/eval_vector_only.json`) | 65.6% | 84.4% | 0.73 | - | - |
| + Reranking (`eval/results/eval_rerank.json`) | 68.8% | 81.2% | 0.74 | "which regulation repeals 95/46/EC" | "lawful grounds vs special categories", "non-EU business / France" |
| + BM25 (`eval/results/eval_results.json`) | 68.8% | 81.2% | 0.74 | none | none |
| + Threshold -4.5 + query rewriting + hardened prompt (full run) | 68.8% | 81.2% | 0.74 | none | none |

**Takeaway:** reranking improves the top position (R@1, MRR) but hurts long two-part questions:
the cross-encoder scores each chunk against the *whole* question, so a chunk that answers only one
half loses to chunks that partly match both. We kept reranking because its score drives the
refusal threshold and it improves R@1; the two regressions are logged above as open issues.


## Tier 1 changes (regression check, retrieval only, 36 questions)

| Change | R@1 | R@5 | MRR | Fixed | Broke |
|---|:---:|:---:|:---:|---|---|
| Base (fixed chunks, rerank, BM25, rewrite) | 64% | 81% | 0.71 | - | - |
| + Article-aware chunking | 75% | 86% | 0.79 | "lawful grounds vs special categories", "non-EU business / France" (both reranking regressions) | none |
| + Decomposition | 78% | 83% | 0.80 | - | "which regulation repeals 95/46/EC" (split into 2 sub-questions) -> decomposition kept OFF |
| + Expansion | 75% | 83% | 0.78 | - | lower R@1 / MRR -> kept OFF |

| Question | Problem after Tier 1 | Fix applied | Fixed? |
|---|---|---|:---:|
| The 3 ambiguous questions | Answered with a guess | Clarifying question (`USE_CLARIFY`) | ✅ 3/3 |
| Out-of-scope questions (weather, stock price...) | Got a clarifying question instead of a refusal | Threshold checked BEFORE the clarity check | ✅ (re-run full eval to confirm) |
| Who is defined as a 'controller' in Article 4(7)? | New wrong refusal: Art. 4 chunk at rank 1, but not the paragraph with (7) | Agent: `define_term` tool. RAG: open | 🟡 |
| Can I take back my consent whenever I want...? | Refused by the threshold (score -5.55): article chunks change the score scale | Re-tune `RERANK_THRESHOLD` on the article index with `threshold_sweep.py` | ❌ open |
| What specific provisions are outlined in Article 2(2)(c)? | Still a retrieval miss | Agent: `get_article("GDPR", "2")` | 🟡 agent only |
| What is the purpose of the first one? (follow-up) | Rewritten correctly, still missed (NIST page) | Open | ❌ |

## Final run (`eval/results/eval_final_full.json`, full, article index, 36 answerable questions)

8 answerable questions were not answered (refused or got a clarifying question). 🟡 = fix in the
code, not yet confirmed by a new `eval_runner.py --full` run.

| Question | Rank | Top rerank | What happened | Fix applied | Fixed? |
|---|:---:|:---:|---|---|:---:|
| How are restrictions by legislative measures specified regarding scope, subject matter, and controller safeguards? | 1 | 4.8 | Over-clarified: asked "Which document?" | Clarity check skipped for questions > `CLARIFY_MAX_WORDS`, prompt: not naming the document is not a reason to ask | 🟡 |
| What rules govern data anonymization and user privacy protection in this text? | - | 1.5 | Over-clarified ("in this text" read as vague) | Same | 🟡 |
| What were the administrative fine limits for data breaches under the 1995 Data Protection Directive? | - | 1.5 | Over-clarified (also a label issue, see above: not in the corpus) | Same | 🟡 |
| And how long must they keep the automatically generated logs? (follow-up) | 1 | 9.8 | Over-clarified although the history says "high-risk AI providers" | Clarity check skipped whenever there is history | 🟡 |
| If a non-EU business tracks user habits of people living in France ... parental consent for 14-year-olds? | 2 | -5.84 | Refused by the threshold: -4.5 was tuned on the fixed-chunk index, article chunks score lower | Re-tune `RERANK_THRESHOLD` with `threshold_sweep.py` (team sets the value) | 🟡 |
| Can I take back my consent whenever I want, and does that make everything they did before illegal? | 1 | -5.89 | Same (threshold) | Same | 🟡 |
| Who is defined as a 'controller' in Article 4(7)? | 1 | 1.8 | LLM refused: the Art. 4 chunk at rank 1 does not contain paragraph (7) | Agent: `define_term` tool (RAG: open) | 🟡 |
| What specific provisions are outlined in Article 2(2)(c)? | - | 1.2 | Exact reference not retrieved | Agent: `get_article` tool (RAG: open) | 🟡 |

The 4 over-clarified questions now pass `scripts/eval/clarify_check.py` (7/7 with the 3 ambiguous
questions still asked back, checked 3 times).
