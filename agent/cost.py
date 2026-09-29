PRICES = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},      # $ / 1M tokens
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

total_cost = 0.0

def track_cost(response, is_embedding=False):
    global total_cost
    model = response.model  # e.g. "gpt-4o-mini-2024-07-18", so match on the prefix
    prices = next((p for name, p in PRICES.items() if model.startswith(name)),
                  {"input": 0.0, "output": 0.0})

    if is_embedding:
        tokens = response.usage.total_tokens
        cost = tokens / 1_000_000 * prices["input"]
    else:
        usage = response.usage
        cost = (
            usage.prompt_tokens / 1_000_000 * prices["input"]
            + usage.completion_tokens / 1_000_000 * prices["output"]
        )

    total_cost += cost
    return cost

def print_total_cost():
    print(f"Overall cost for session : ${total_cost:.4f}")