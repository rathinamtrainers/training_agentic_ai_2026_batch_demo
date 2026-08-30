"""Tokens are what the window holds and what the invoice counts -- and retrieval writes most of the bill.

One real Gemini call per passage budget, on the course's own credentials.
    uv run --project ../demo python 01_tokens_and_the_meter.py
"""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))     # the course's own .env
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()

# Hand-entered from https://ai.google.dev/gemini-api/docs/pricing, checked 2026-08-15,
# exactly as demo/usage.py does it. USD per 1,000,000 tokens.
PRICE_IN, PRICE_OUT = 0.75, 3.75

QUESTION = "Is an escape of water from a neighbouring flat covered?"
PASSAGES = [
    "[01_escape_of_water.md §4] Escape of water from a neighbouring flat is covered. Excess GBP 350.",
    "[08_excess_and_settlement.md §2] The standard buildings excess is GBP 250.",
    "[03_gradual_seepage.md §1] Damage caused by gradual seepage over weeks or months is excluded.",
    "[11_broker_commission.md §6] Broker commission is settled monthly in arrears.",
    "[07_complaints_timescales.md §3] A final response to a complaint is due within eight weeks.",
]

for count in (5, 2):
    prompt = ("Answer from these passages only, citing [file §clause].\n\n"
              + "\n".join(PASSAGES[:count]) + f"\n\nQuestion: {QUESTION}")
    reply = client.models.generate_content(model=MODEL, contents=prompt)
    used = reply.usage_metadata
    cost = (used.prompt_token_count * PRICE_IN + used.candidates_token_count * PRICE_OUT) / 1_000_000
    print(f"\n=== {count} passages attached | model {MODEL}")
    print(reply.text.strip())
    print(f"    prompt {used.prompt_token_count} tokens, output {used.candidates_token_count},"
          f" thinking {used.thoughts_token_count}, total {used.total_token_count}"
          f" = ${cost:.6f} at the 2026-08-15 price list")
