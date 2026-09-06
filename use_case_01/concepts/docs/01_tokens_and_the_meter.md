# 01 — Tokens and the meter

`../01_tokens_and_the_meter.py`

## Summary

The script asks Gemini the same question twice. The only thing that changes
between the two calls is how many retrieved passages are pasted into the prompt:
five the first time, two the second. It then prints the real token counts the API
reported and multiplies them by the published price.

The point is that **retrieval writes most of the bill.** The question is one
sentence. The passages are what fill the window, and the passages are chosen by
your retriever, not by your user. Tune `TOP_K` and you have moved the invoice.

It is the first script in the sequence because everything after it — chunk size,
top-k, whether to rerank, whether to stream — is a trade against the two numbers
this script prints.

---

## Aspect by aspect

### 1. Configuration

Identical to every other concept script: `.env` is loaded relative to `__file__`,
`GOOGLE_GENAI_USE_VERTEXAI` is derived from `GENAI_BACKEND`, and `genai.Client()`
picks the rest out of the environment. See
[`04_function_call_round_trip.md`](04_function_call_round_trip.md) for the full
explanation of that preamble; it is not repeated in these notes.

### 2. The price list is hand-entered, and dated

```python
# Hand-entered from https://ai.google.dev/gemini-api/docs/pricing, checked 2026-08-15,
# exactly as demo/usage.py does it. USD per 1,000,000 tokens.
PRICE_IN, PRICE_OUT = 0.75, 3.75
```

There is no API that returns the price. It is typed in by a human, from a page
that changes, and the comment carries the date it was checked. `demo/usage.py`
does the same thing for the same reason.

Two prices, not one, and output is five times input. That ratio is worth pausing
on: a long prompt is cheap per token and a long answer is expensive per token,
which is exactly the opposite of where most people's intuition sits. Instructing
the model to answer in two sentences is a cost control.

### 3. The passages are pre-formatted with their citation

```python
PASSAGES = [
    "[01_escape_of_water.md §4] Escape of water from a neighbouring flat is covered. Excess GBP 350.",
    ...
]
```

Each string already carries `[file §clause]` at the front. That is not decoration
— it is how the model is able to cite. The model can only reproduce a citation it
was given, so the citation has to be inside the text that goes into the window.
Script 16 checks the other end of that pipe.

Five passages, and only the first genuinely answers the question. The other four
are realistic retriever noise: a related excess, an exclusion, and two rows about
entirely different subjects. Real top-k retrieval always returns k, relevant or
not — a point script 10 makes explicitly.

### 4. The two calls

```python
for count in (5, 2):
    prompt = ("Answer from these passages only, citing [file §clause].\n\n"
              + "\n".join(PASSAGES[:count]) + f"\n\nQuestion: {QUESTION}")
    reply = client.models.generate_content(model=MODEL, contents=prompt)
```

Plain text prompts, no tools, no schema. Nothing is being tested except size.
`PASSAGES[:count]` is the whole experiment: 5 passages, then 2.

### 5. The meter

```python
used = reply.usage_metadata
cost = (used.prompt_token_count * PRICE_IN + used.candidates_token_count * PRICE_OUT) / 1_000_000
```

`usage_metadata` comes back on every response and is the authoritative count —
not an estimate, not `len(text) / 4`. Four fields are printed:

- **`prompt_token_count`** — everything you sent: instruction, passages,
  question. This is the number retrieval controls.
- **`candidates_token_count`** — the visible answer.
- **`thoughts_token_count`** — reasoning tokens on the 3.x thinking models. They
  are billed at the output rate and they are *not* in `candidates_token_count`,
  so a cost calculation that ignores them under-reports. This script's `cost`
  line does ignore them, which is worth saying out loud when teaching it: the
  printed dollar figure is a floor, and `total_token_count` is the honest total.
- **`total_token_count`** — the sum, and the number to compare against the
  model's context window.

Dividing by `1_000_000` at the end, once, keeps the arithmetic in whole tokens
until the last step.

### 6. What the output shows

Two things move together, and one does not. The prompt count falls sharply
between the two runs, because three passages left the window. The output count
barely moves, because the answer is the same length either way. And the answer
itself usually stays correct — which is the uncomfortable part: the three dropped
passages cost real money and added nothing. That is the argument for a reranker
with a floor, which is script 13.

---

## What to take away

- A token is the unit of both the context window and the invoice.
- The user writes the question; your retriever writes the prompt. Cost is a
  retrieval decision.
- Output costs several times what input costs. Short answers are cheap answers.
- Thinking tokens are billed and are counted separately from the visible answer.
  Use `total_token_count` when you want the truth.
- Read `usage_metadata`. Never estimate.

## Related

- `13_the_reranker_and_the_floor.py` — dropping the passages that were not
  earning their place in the window.
- `07_the_cap_and_the_budget.py` — the same meter used as a stop condition.
- `demo/usage.py` — the same price table, in the service.
- `../run_logs/01_tokens_and_the_meter_RUN_LOG.md` — recorded runs.
