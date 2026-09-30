import time

from app.core import CHAT_MODEL, TOP_K, MIN_SCORE, REFUSAL, track_cost
from app.embeddings import client
from app.retrieval import retrieve

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the question based ONLY "
    "on the provided context. If the context doesn't contain the "
    f"answer, say '{REFUSAL}' "
    "Always cite which source your answer comes from. "
    "If the question has several parts, answer each part. "
    "If the question is vague, say what is unclear and ask the user "
    "to be more specific."
)


def safe_chat(messages, max_tokens=300, retries=3, delay=2):
    """Appelle l'API avec quelques essais. Renvoie None si tout échoue."""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens,
            )
            track_cost(response)
            return response
        except Exception as e:
            print(f"Erreur API (essai {attempt + 1}/{retries}) : {e}")
            time.sleep(delay * (attempt + 1))
    return None


def generate_answer(query, retrieved_chunks):
    context = "\n\n".join(
        f"[Source: {c['source']} p.{c['page']}]\n{c['text']}"
        for c in retrieved_chunks
    )
    response = safe_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ])
    if response is None:
        return "Sorry, the API is not responding. Please try again."
    return response.choices[0].message.content


def answer_question(query, index, chunks, k=TOP_K):
    results = retrieve(query, index, chunks, k=k)

    if results is None:
        results = retrieve(query, index, chunks, k=k)

    answer = generate_answer(query, results)

    if REFUSAL.lower().rstrip(".") in answer.lower():  # type: ignore
        return answer, []
    return answer, results

    