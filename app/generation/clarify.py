"""Detect vague questions and ask the user to clarify instead of guessing an answer."""
from app.core import CLARIFY_MAX_WORDS
from app.generation.llm_json import ask_json

CLARIFY_PREFIX = "Could you clarify your question?"

PROMPT = (
    "You check questions sent to an assistant about three documents: the GDPR, the EU AI Act "
    "and the NIST AI Risk Management Framework. Ask the user to clarify ONLY when the question "
    "is a single generic concept that more than one document regulates, with nothing that says "
    "which one is meant. Not naming the document is NOT a reason to ask when the topic points to "
    "one law (fines, data protection, privacy, anonymisation, 95/46/EC -> GDPR; high-risk AI, logs, "
    "providers -> AI Act; AI risk management -> NIST). Words like 'this text' do not matter.\n"
    "Examples:\n"
    "'What about the obligations?' -> ask (obligations of whom, under which law?)\n"
    "'What are the rules on transparency?' -> ask (GDPR Art. 12 or AI Act transparency duties?)\n"
    "'What does the law say about penalties?' -> ask (GDPR or AI Act penalties?)\n"
    "'What rules govern pseudonymisation and data minimisation in this regulation?' -> clear (GDPR)\n"
    "'What were the maximum fines under the old directive?' -> clear (GDPR context)\n"
    "'How are the duties of deployers of high-risk systems specified?' -> clear (AI Act)\n"
    "'What does Article 6(1)(f) provide?' -> clear (a specific article reference is always clear)\n"
    "When in doubt, answer clear. "
    'Reply in JSON: {"clear": true} or {"clear": false, "ask": "<one short clarifying question, '
    'offering 2-3 concrete options>"}'
)


def check_clarity(question, history=None):
    """None if the question is clear, otherwise the clarification message to show the user."""
    if history:                         # a follow-up always has context -> never ask back
        return None
    if len(question.split()) > CLARIFY_MAX_WORDS:   # long questions carry enough detail
        return None
    result = ask_json(PROMPT, f"Question: {question}")
    if not result or result.get("clear", True):
        return None                     # clear, or the check failed -> answer normally
    return f"{CLARIFY_PREFIX} {result.get('ask', '').strip()}".strip()
