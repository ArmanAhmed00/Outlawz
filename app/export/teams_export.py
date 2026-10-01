"""Post a whole conversation (questions, answers, sources) to Teams as one Adaptive Card."""
import json
from datetime import datetime
from agent.tools.messaging import post_card

MAX_TOTAL_CHARS = 15000      # Teams rejects cards above ~28 KB: long answers are shortened
MAX_CARD_BYTES = 24000       # safety margin under the Teams limit


def chat_to_card_body(turns):
    budget = max(200, min(1500, MAX_TOTAL_CHARS // max(len(turns), 1)))
    body = [
        {"type": "TextBlock", "text": "Outlawz - conversation export", "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "isSubtle": True, "size": "Small", "wrap": True,
         "text": f"{datetime.now():%d %B %Y, %H:%M} · {len(turns)} questions · GDPR, EU AI Act, NIST AI RMF"},
    ]
    shortened = False
    for i, t in enumerate(turns, 1):
        answer = t["answer"]
        if len(answer) > budget:
            answer, shortened = answer[:budget].rsplit(" ", 1)[0] + " [...]", True
        items = [{"type": "TextBlock", "text": f"Q{i}. {t['question']}", "weight": "Bolder",
                  "color": "Accent", "wrap": True},
                 {"type": "TextBlock", "text": answer, "wrap": True}]
        if t.get("sources"):
            items.append({"type": "TextBlock", "text": "Sources: " + "; ".join(t["sources"]),
                          "isSubtle": True, "size": "Small", "wrap": True})
        body.append({"type": "Container", "separator": True, "spacing": "Medium", "items": items})
    if shortened:
        body.append({"type": "TextBlock", "isSubtle": True, "size": "Small", "wrap": True,
                     "text": "Long answers were shortened. Download the PDF from the app for the full text."})
    return body


def post_chat_to_teams(turns):
    """Returns (ok, detail). Very long chats: only the most recent questions that fit are sent."""
    if not turns:
        return False, "nothing to send"
    kept = list(turns)
    body = chat_to_card_body(kept)
    while len(json.dumps(body)) > MAX_CARD_BYTES and len(kept) > 1:
        kept = kept[1:]                                   # drop the oldest question
        body = chat_to_card_body(kept)
    if len(kept) < len(turns):
        body.insert(2, {"type": "TextBlock", "isSubtle": True, "size": "Small", "wrap": True,
                        "text": f"Only the last {len(kept)} of {len(turns)} questions fit in one Teams message."})
    return post_card(body)
