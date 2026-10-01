"""send_message: the ONLY tool that acts on the outside world, so it is gated by a human.

The agent can only PROPOSE a message (send_message adds it to PROPOSALS). Nothing is posted
until a person clicks "Approve" in the UI, which calls post_to_teams(). In evals and the
injection test, fake_decline() plays the person saying no, and logs the proposal.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
PROPOSALS = []       # messages proposed during the current run (cleared before each run)


def send_message(message: str) -> str:
    PROPOSALS.append(message)
    return ("Message PROPOSED, NOT sent. A person must approve it first. Tell the user the "
            "message is ready and waiting for their approval below; do not claim it was sent.")


def post_card(body):
    """Post an Adaptive Card (list of card elements) to the Teams webhook. Returns (ok, detail)."""
    url = os.getenv("TEAMS_WEBHOOK_URL")
    if not url:
        return False, "TEAMS_WEBHOOK_URL is missing in .env"
    payload = {      # Teams Workflows ("Post to a channel when a webhook request is received")
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4",
                "body": body,
            },
        }],
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as e:
        return False, f"request failed: {e}"
    return r.status_code in (200, 202), f"HTTP {r.status_code}"


def post_to_teams(text):
    """Post one message (used after the user approves a send_message proposal)."""
    return post_card([{"type": "TextBlock", "text": "Outlawz assistant", "weight": "Bolder"},
                      {"type": "TextBlock", "text": text, "wrap": True}])


def fake_decline(log):
    """Stand-in for the person: declines every proposal, logs it, posts nothing."""
    declined = list(PROPOSALS)
    log.extend(declined)
    PROPOSALS.clear()
    return declined
