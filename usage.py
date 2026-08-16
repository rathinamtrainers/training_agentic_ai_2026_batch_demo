"""The meter. Tokens in, tokens out, cached tokens, and what that costs.

Slide 22: "you cannot control a number you never look at." From tonight, every
call prints its usage. This module is the printer; 03_token_cost.py wires it
into the agent as an after_model_callback, which is the hook ADK gives you for
"I want to see every model response before the runtime does anything with it".
"""

import datetime

from google.genai import types

# --- The price list ---------------------------------------------------------
#
# HAND-ENTERED FROM THE VENDOR'S PUBLIC PAGE. Verify it before you quote a
# number in a meeting -- prices move, and a stale price list is worse than no
# price list because it sounds authoritative.
PRICE_LIST_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"
PRICE_LIST_CHECKED = "2026-08-15"

# These are INTRODUCTORY rates. The published page says the 3.x Flash prices
# double on 1 January 2027. This course finishes on 22 November 2026, so the
# numbers below are the ones that apply all sixteen weeks -- but anyone
# re-running this lab in 2027 is being told the wrong figure, so the code says
# so out loud rather than trusting a comment nobody reads.
PRICES_VALID_UNTIL = "2026-12-31"
PRICES_AFTER = "input $1.50, output $7.50, cached input $0.15 per 1M from 2027-01-01"

# US dollars per 1,000,000 tokens, paid tier, text.
#
# Slide 21 teaches "cache ~ 10% of input" as a rule of thumb. On this model it
# is not a rule of thumb, it is exact: $0.075 cached against $0.75 input is
# 10.0%, and it stays 10.0% after the January increase ($0.15 / $1.50). Say
# that on the night. Other vendors sit near the same ratio -- check yours, do
# not assume it.
PRICES_USD_PER_MILLION = {
    "gemini-3.7-flash": {"input": 0.75, "output": 3.75, "cached_input": 0.075},
    # Same family, same published rates, if a model has to be swapped live.
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75, "cached_input": 0.075},
    # 3.5 Flash is priced differently -- and its cached rate is also exactly
    # 10% of its input rate.
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00, "cached_input": 0.15},
    # gemini-2.5-flash is deliberately absent. It was retired for new API keys
    # in August 2026, and a price for a model nobody can call is a trap.
}
# Not modelled here, and worth naming out loud: Gemini also bills cache
# *storage* per token per hour. Tonight's calls cache nothing, so it is zero.


def cost_of(usage: types.GenerateContentResponseUsageMetadata, model: str) -> dict | None:
    """Turn one call's usage metadata into money.

    The subtraction on the second line is the part people get wrong:
    prompt_token_count ALREADY INCLUDES the cached tokens. Bill the cached ones
    at the cache rate and only the remainder at the full input rate, or you
    will overstate your own bill and under-value your own caching.
    """
    prices = PRICES_USD_PER_MILLION.get(model)
    if prices is None:
        return None

    prompt = usage.prompt_token_count or 0
    cached = usage.cached_content_token_count or 0
    fresh_input = max(prompt - cached, 0) + (usage.tool_use_prompt_token_count or 0)

    # Thinking tokens are output tokens. They are billed as output even though
    # you never see them, which is why a "short" answer can cost more than it
    # looks. This is a real line on a real bill, so it goes in the sum.
    output = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)

    per_million = 1_000_000
    return {
        "fresh_input_tokens": fresh_input,
        "cached_input_tokens": cached,
        "output_tokens": output,
        "total_tokens": usage.total_token_count or (fresh_input + cached + output),
        "input_usd": fresh_input * prices["input"] / per_million,
        "cached_usd": cached * prices["cached_input"] / per_million,
        "output_usd": output * prices["output"] / per_million,
    }


def print_usage(label: str, usage, model: str) -> dict | None:
    """One call, one small table. Read out loud from the projector."""
    if usage is None:
        print(f"  [usage] {label}: the response carried no usage metadata")
        return None

    money = cost_of(usage, model)
    print(f"  [usage] {label}")
    print(f"          input tokens        {usage.prompt_token_count or 0:>8,}"
          f"   (of which cached: {usage.cached_content_token_count or 0:,})")
    print(f"          output tokens       {usage.candidates_token_count or 0:>8,}")
    if usage.thoughts_token_count:
        print(f"          thinking tokens     {usage.thoughts_token_count:>8,}   billed as output")
    print(f"          total tokens        {usage.total_token_count or 0:>8,}")

    if money is None:
        print(f"          cost                unknown -- no price on file for {model!r}")
        print(f"          add it to usage.py, from {PRICE_LIST_SOURCE}")
        return None

    total = money["input_usd"] + money["cached_usd"] + money["output_usd"]
    print(f"          cost  input          ${money['input_usd']:.8f}")
    print(f"                cached input   ${money['cached_usd']:.8f}")
    print(f"                output         ${money['output_usd']:.8f}")
    print(f"                THIS CALL      ${total:.8f}")
    return money


def make_usage_printer(model: str):
    """Returns (callback, totals).

    `callback` is an ADK after_model_callback: ADK hands it every model
    response before the runtime acts on it. Returning None means "carry on,
    I only wanted to look". `totals` accumulates across the calls in a turn --
    which is the point of slide 21: one user question is not one model call.
    """
    totals = {"calls": 0, "fresh_input": 0, "cached_input": 0, "output": 0, "usd": 0.0}

    def print_model_usage(callback_context, llm_response):
        usage = getattr(llm_response, "usage_metadata", None)
        if usage is None:
            return None

        totals["calls"] += 1
        money = print_usage(f"model call #{totals['calls']}", usage, model)
        if money:
            totals["fresh_input"] += money["fresh_input_tokens"]
            totals["cached_input"] += money["cached_input_tokens"]
            totals["output"] += money["output_tokens"]
            totals["usd"] += money["input_usd"] + money["cached_usd"] + money["output_usd"]
        return None  # do not replace the response; we are only watching

    return print_model_usage, totals


def print_turn_total(totals: dict) -> None:
    """The number that actually matters: cost per TURN, not per call."""
    print(f"\n  [usage] one user question cost {totals['calls']} model call(s)")
    print(f"          input {totals['fresh_input']:,} fresh + {totals['cached_input']:,} cached"
          f" · output {totals['output']:,}")
    print(f"          TURN TOTAL     ${totals['usd']:.8f}")
    print(f"          × 1,000,000 turns  ${totals['usd'] * 1_000_000:,.2f}")
    print(f"          (prices hand-checked {PRICE_LIST_CHECKED} against {PRICE_LIST_SOURCE})")
    if datetime.date.today().isoformat() > PRICES_VALID_UNTIL:
        print(f"          WARNING: those introductory rates ended {PRICES_VALID_UNTIL}."
              f" Published now: {PRICES_AFTER}.")
        print("          The figures above are therefore too low. Update usage.py.")
