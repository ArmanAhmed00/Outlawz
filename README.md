# Outlawz


## Ablation table (retrieval only, 32 questions with expected pages)

| Version              | Recall@1 | Recall@3 | Recall@5 | MRR  | Latency |
|----------------------|:--------:|:--------:|:--------:|:----:|:-------:|
| Vector only (FAISS)  |     66     |    81      |     84    |    0.73  |    0.17   |
| + Reranking          |       69   |      81    |       81   |    0.74  |       0.29  |
| + BM25 (hybrid, RRF) |       69   |       81   |        81  |     0.74 |       0.30  |

**Kept:** ... (one line: which config you keep and why)