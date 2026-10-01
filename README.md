# Outlawz

RAG assistant (and agent) that answers questions about AI and data-protection law, with
page-level citations: the **GDPR** (Regulation (EU) 2016/679), the **EU AI Act**
(Regulation (EU) 2024/1689) and the **NIST AI Risk Management Framework 1.0**.

**Team:** _<name 1>_, _<name 2>_, _<name 3>_

## How to run

```bash
uv sync                                         # install dependencies (Python 3.12)
uv run python scripts/build_index.py            # only once: chunk + embed + FAISS index
uv run streamlit run app/app.py                 # web UI
uv run python scripts/chat_rag.py               # RAG chat in the terminal (with memory)
uv run python scripts/eval_runner.py            # eval, retrieval only (cheap)
uv run python scripts/eval_runner.py --full     # eval with generated answers
```

## Pipeline

```
question (+ last 2 exchanges)
  -> follow-up? rewrite into a standalone question (gpt-4o-mini)
  -> FAISS top-20 (meaning) + BM25 top-20 (keywords) -> RRF merge
  -> cross-encoder rerank -> top 5
  -> best reranker score < -4.5 ?  -> refuse
  -> gpt-4o-mini answers with citations (source + page)
```

Every component is behind a flag in `app/core.py` (`USE_RERANK`, `USE_BM25`, `USE_REWRITE`)
and can be switched off from the eval runner (`--no-rerank`, `--no-bm25`, `--no-rewrite`).

## Ablation table (retrieval only, 32 questions with expected pages)

| Version              | Recall@1 | Recall@3 | Recall@5 | MRR  | Latency (s) |
|----------------------|:--------:|:--------:|:--------:|:----:|:-----------:|
| Vector only (FAISS)  |   66%    |   81%    |   84%    | 0.73 |    0.17     |
| + Reranking          |   69%    |   81%    |   81%    | 0.74 |    0.29     |
| + BM25 (hybrid, RRF) |   69%    |   81%    |   81%    | 0.74 |    0.30     |

**Kept:** vector + reranking + BM25. Reranking puts the right chunk first more often
(R@1 +3 pts, MRR +0.01) and its score cleanly separates in-scope from out-of-scope
questions, which we use for the refusal threshold. BM25 is kept for exact legal
references (article numbers); it shows no gain here because the eval set has no
exact-term questions yet.

**Analysis:** R@3 = R@5 in every configuration: when the right page is retrieved it is
already in the top 3. The remaining misses are all-or-nothing (the page is not among the
candidates), so they come from labels and corpus coverage, not ranking (see
`scripts/FAILURE_LOG.md`). Reranking adds ~0.12 s per question. With 32 questions,
one question = ~3 points.

## Confidence threshold (reranker score)

We refuse when the cross-encoder score of the top chunk is below **-4.5** (FAISS and RRF
scores are on other scales and not comparable). Tuned with `scripts/threshold_sweep.py` on
11 should-refuse questions (4 out-of-scope, 4 on-topic unanswerable, 3 ambiguous) and
32 answerable ones:

| Threshold | Correct refusals (11) | Wrong refusals (32) |
|:---:|:---:|:---:|
| -6       | 4/11 | 1/32 |
| **-4.5** | **6/11** | **1/32** |
| -2       | 9/11 | 2/32 |
| 0        | 9/11 | 4/32 |

**Why -4.5:** it sits in the gap between out-of-scope questions (-11 to -5.3) and the lowest
correctly retrieved answerable question (-3.4). Moving to -2 would refuse 3 more questions
but would also refuse a correctly retrieved answerable one ("Can I take back my consent...",
score -3.4), and the extra unanswerable one is already refused by the LLM itself.

**Final result (`eval_runner.py --full`, threshold + LLM refusal together):**

| Group | Result |
|---|:---:|
| Out-of-scope | 4/4 refused |
| On-topic unanswerable | 4/4 refused (2 by the threshold, 2 by the LLM) |
| Ambiguous | 0/3 refused (answered with a guess instead of asking to clarify) |
| Answerable, wrongly refused | 6/32 |

The 6 wrong refusals: 4 are questions whose page is not retrieved (refusing is the safe
outcome there), 2 are retrieved at rank 1 but the LLM judged the chunk incomplete
("six principles", "data portability vs erasure") -> generation issue, logged in
`scripts/FAILURE_LOG.md`. Ambiguous questions are the main weakness: the threshold cannot
catch them (they are on-topic), so the fix belongs in the prompt.

## Conversation memory

The last 2 exchanges are sent to the model with each new question (long answers cut to
500 characters) - in the RAG pipeline and in the agent/UI. Memory alone does not fix
retrieval (it would still search with the bare follow-up), so follow-ups are first
rewritten into standalone questions (one gpt-4o-mini call, skipped on the first turn).

| Follow-up questions (n=_X_) | Recall@1 | Recall@5 | MRR |
|---|:---:|:---:|:---:|
| Memory only (`--no-rewrite`) |  |  |  |
| + Query rewriting            |  |  |  |

_TODO: fill after adding the follow-up questions (see below)._

## Useful scripts

| Script | What it does |
|---|---|
| `scripts/eval_runner.py` | Recall@1/3/5, MRR, latency, by category / difficulty, failures |
| `scripts/threshold_sweep.py` | Correct vs wrong refusals for a range of thresholds |
| `scripts/find_page.py` | Finds the page(s) containing a phrase, to fill `expected_chunks` |
| `scripts/check_questions.py` | Validates `data/questions.json` |
| `scripts/chat_rag.py` | Terminal chat with memory (shows the rewritten query) |
