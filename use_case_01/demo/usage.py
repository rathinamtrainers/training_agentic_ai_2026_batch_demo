"""The meter. Tokens in, tokens out, and what that costs.

"You cannot control a number you never look at." Every answer this service
produces prints its own token count and its own price, because the cheapest
moment to discover that a question costs eight cents is the moment you ask it,
not the invoice at the end of the month. Northwind's margins are thin: the cost
of answering a question matters as much as the answer.

The price list below is HAND-ENTERED from the vendor's public page and dated.
Verify it before you quote a number in a meeting -- prices move, and a stale
price list is worse than no price list, because it sounds authoritative.
"""

import config

PRICE_LIST_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
PRICE_LIST_CHECKED = "2026-08-15"
PRICES_VALID_UNTIL = "2026-12-31"

# US dollars per 1,000,000 tokens, paid tier, text.
PRICES_USD_PER_MILLION = {
    "gemini-3.7-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
}


def cost_usd(model: str, prompt_tokens: int, output_tokens: int) -> float | None:
    """None means: this model is not in the hand-entered list. Print 'unpriced'
    rather than a made-up number."""
    price = PRICES_USD_PER_MILLION.get(model)
    if not price:
        return None
    return (prompt_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


def report(model: str, prompt_tokens: int, output_tokens: int) -> str:
    total = prompt_tokens + output_tokens
    money = cost_usd(model, prompt_tokens, output_tokens)
    if money is None:
        return (f"{total} tokens ({prompt_tokens} in, {output_tokens} out)"
                f" -- {model} is not in the price list, so this one is unpriced")
    return (f"{total} tokens ({prompt_tokens} in, {output_tokens} out)"
            f" = ${money:.6f} at the {PRICE_LIST_CHECKED} price list")


def budget_note() -> str:
    return (
        f"price list hand-entered {PRICE_LIST_CHECKED} from {PRICE_LIST_SOURCE},"
        f" valid to {PRICES_VALID_UNTIL}. Model in use: {config.CHAT_MODEL}."
    )
