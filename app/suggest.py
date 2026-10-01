from app.core import CHAT_MODEL, track_cost
from app.embeddings import client

PROMPT = (
    "Suggest 3 short follow-up questions the user could ask next, based on this exchange. "
    "They must be answerable from the GDPR, the EU AI Act or the NIST AI RMF. "
    "Write them as natural follow-ups (they may refer to the previous answer). "
    "Return one question per line, no numbering."
)


def suggest_followups(question, answer):
    """3 clickable follow-up questions (1 small API call). Empty list if it fails."""
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL, temperature=0, max_tokens=90,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer[:1500]}"},
            ],
        )
        track_cost(response)
        lines = [l.strip(" -•").strip() for l in response.choices[0].message.content.splitlines()]
        return [l for l in lines if l.endswith("?")][:3]
    except Exception:
        return []
