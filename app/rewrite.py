from app.core import CHAT_MODEL, track_cost
from app.embeddings import client
from app.memory import recent_history

REWRITE_PROMPT = (
    "Rewrite the user's last question as a standalone question. Use the conversation "
    "only to resolve references such as 'it', 'that article', 'and for ...'. "
    "If the question is already standalone, return it unchanged. "
    "Return only the question, nothing else."
)


def rewrite_query(question, history):
    """Turn a follow-up into a standalone question for retrieval (1 cheap call)."""
    if not history:              # first turn: nothing to resolve, no API call
        return question
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent_history(history))
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL, temperature=0, max_tokens=80,
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": f"Conversation:\n{convo}\n\nLast question: {question}"},
            ],
        )
        track_cost(response)
        return response.choices[0].message.content.strip()
    except Exception:
        return question          # if the API fails, search with the original question
