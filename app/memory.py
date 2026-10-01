from app.core import MAX_HISTORY_TURNS, HISTORY_CHAR_LIMIT


def recent_history(history):
    """Last N exchanges as chat messages; long answers cut to keep the cost down."""
    if not history:
        return []
    recent = history[-2 * MAX_HISTORY_TURNS:]   # 2 messages per exchange
    return [{"role": m["role"], "content": m["content"][:HISTORY_CHAR_LIMIT]} for m in recent]
