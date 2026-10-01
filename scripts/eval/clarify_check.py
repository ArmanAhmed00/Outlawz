# Run check_clarity on the 3 ambiguous + 4 over-clarified questions (7 cheap calls, no retrieval).
# Usage: uv run python scripts/eval/clarify_check.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.generation.clarify import check_clarity

LOGS_HISTORY = [{"role": "user", "content": "What are the obligations of providers of high-risk AI systems?"}]

# (question, history, expected)
CASES = [
    ("Tell me about the requirements.", None, "ask"),
    ("What are the rules regarding consent?", None, "ask"),
    ("How does the law deal with exceptions?", None, "ask"),
    ("How are restrictions by legislative measures specified regarding scope, subject matter, and controller safeguards?", None, "clear"),
    ("What rules govern data anonymization and user privacy protection in this text?", None, "clear"),
    ("What were the administrative fine limits for data breaches under the 1995 Data Protection Directive?", None, "clear"),
    ("And how long must they keep the automatically generated logs?", LOGS_HISTORY, "clear"),
]

ok = 0
for question, history, expected in CASES:
    ask = check_clarity(question, history)
    got = "ask" if ask else "clear"
    ok += got == expected
    print(f"{'✅' if got == expected else '❌'} {got:5} (expected {expected:5}) | {question[:70]}")
    if ask:
        print(f"        -> {ask}")
print(f"\n{ok}/{len(CASES)} as expected")
