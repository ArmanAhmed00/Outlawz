"""One small gpt-4o-mini call that must answer in JSON (used by clarify / query planning)."""
import json
from app.core import CHAT_MODEL, track_cost
from app.embeddings import client


def ask_json(system, user, max_tokens=150):
    """Return the parsed JSON dict, or None if the call or the parsing fails."""
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL, temperature=0, max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        track_cost(response)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[ask_json] failed: {e}")
        return None
