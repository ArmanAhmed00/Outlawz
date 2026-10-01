"""Turn one question into the list of search queries used for retrieval.

- decomposition: "How do X and Y differ?" -> ["What is X?", "What is Y?"]
- expansion: 2 rephrasings with the vocabulary of the legal texts
Flags are read at call time (app.core), so the eval runner can switch them.
"""
import app.core as core
from app.generation.llm_json import ask_json

DECOMPOSE_PROMPT = (
    "You prepare search queries for documents about the GDPR, the EU AI Act and the NIST AI RMF. "
    "If the question asks about several distinct things (two articles, two rules to compare, "
    "two separate conditions), split it into standalone sub-questions, at most {n}. "
    "Otherwise return the question unchanged as the only item. "
    'Reply in JSON: {{"questions": ["...", "..."]}}'
)

EXPAND_PROMPT = (
    "Rephrase the question in 2 different ways for searching legal texts (GDPR, EU AI Act, "
    "NIST AI RMF): use the official terms these documents would use (e.g. 'erasure' for "
    "'delete', 'controller' for 'company'). Keep the same meaning. "
    'Reply in JSON: {"variants": ["...", "..."]}'
)


def decompose(question):
    result = ask_json(DECOMPOSE_PROMPT.format(n=core.MAX_SUBQUERIES), question)
    subs = [q.strip() for q in (result or {}).get("questions", []) if isinstance(q, str) and q.strip()]
    return subs[:core.MAX_SUBQUERIES] or [question]


def expand(question):
    result = ask_json(EXPAND_PROMPT, question)
    variants = [v.strip() for v in (result or {}).get("variants", []) if isinstance(v, str) and v.strip()]
    return [question] + variants[:2]


def plan_queries(question):
    """Queries to search with. Multi-part questions are split; single ones may be expanded."""
    queries = decompose(question) if core.USE_DECOMPOSE else [question]
    if len(queries) == 1 and core.USE_EXPANSION:
        queries = expand(question)
    return list(dict.fromkeys(queries))   # drop duplicates, keep order
