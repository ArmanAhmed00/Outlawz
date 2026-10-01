"""
PRICES = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},      # $ / 1M tokens
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

total_cost = 0.0


def _get_prices(model_name):
  
    for key, prices in PRICES.items():
        if model_name.startswith(key):
            return prices
    print(f"Warning: no price entry for model '{model_name}', cost will be $0.")
    return {"input": 0.0, "output": 0.0}


def track_cost(response, is_embedding=False):
    global total_cost
    model = response.model
    prices = _get_prices(model)

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
    print(f"This call: ${cost:.6f} | Team total: ${total_cost:.4f} / $5.00")
    return cost


def print_total_cost():
    print(f"Coût total de la session : ${total_cost:.4f}")

"""