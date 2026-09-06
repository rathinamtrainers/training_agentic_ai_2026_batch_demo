# 07 — The cap and the budget

`../07_the_cap_and_the_budget.py`

## Summary

An agent decides for itself when it is finished. So something outside the agent
has to decide when it is not allowed to continue.

The script builds a situation with no exit. The corpus genuinely contains nothing
about tropical fish, the retriever genuinely returns an empty list every time,
and the system instruction genuinely tells the model to *search again with
different wording until you find something*. Left alone, that loop never ends —
the model keeps rephrasing, the tool keeps returning nothing, and the meter keeps
running.

Two ceilings stop it: a cap on tool calls and a budget in tokens. When either
trips, the loop breaks and the user gets a refusal.

> The user gets a refusal, not a bill.

That printed line is the design rule. A runaway agent is not a correctness bug
you notice in testing; it is a cost incident you notice on an invoice.

---

## Aspect by aspect

### 1. The two ceilings

```python
MAX_TOOL_CALLS, TOKEN_BUDGET = 4, 6000          # demo/turn.py's cap; the budget is the second ceiling
```

Two of them, because they fail differently.

**The cap counts steps.** It is the guard against a loop — the same tool called
over and over, each call cheap, the total unbounded. Four is `demo/turn.py`'s
real value, chosen because a legitimate question in this corpus resolves in one
or two searches; four leaves room for a genuine second attempt and no room for a
tenth.

**The budget counts tokens.** It is the guard against size — one enormous
retrieval, a long history, an oversized document. A single tool call can blow a
budget without ever tripping a cap.

Either one alone leaves a gap. Both are needed.

### 2. The instruction that makes it loop

```python
    system_instruction="Answer only from the search tool. If a search returns no passages,"
                       " search again with different wording until you find something."
```

This is deliberately the wrong instruction, and it is realistic — it is close to
what a sensible person writes to stop an agent giving up too early. "Until you
find something" has no exit when there is nothing to find, and the model obeys.

The lesson is not "never write this". It is that an instruction cannot be a
safety control: the model is the thing being constrained, so a rule written in
the prompt is a request, and a rule written in the loop is a fact. That
distinction returns as a security argument in script 15.

### 3. The retriever really is empty

```python
    history.append(types.Content(role="user", parts=[types.Part.from_function_response(
        name="search_knowledge_base", response={"passages": []})]))   # the corpus really has nothing
```

There is no tool function at all in this script. Every search returns
`{"passages": []}`, unconditionally. The question — "what is Northwind's cover
for tropical fish?" — is out of scope by construction, so the empty result is
honest rather than simulated.

An empty list is also the correct thing for a retriever to return. It is what
makes an honest refusal possible, and the tool docstring in script 05 says so
explicitly.

### 4. The accounting

```python
calls, spent = 0, 0
while True:
    reply = client.models.generate_content(model=MODEL, contents=history, config=config)
    spent += reply.usage_metadata.total_token_count
```

Two counters, incremented in the loop that does the work.

`total_token_count`, not `prompt_token_count` — the budget is meant to bound the
whole spend, so thinking tokens and output tokens are included. Script 01 made
the case for that field.

Watch the number climb in the printed output. Each iteration re-sends the entire
history — question, every previous tool request, every empty result — so the
prompt grows monotonically. The token cost of step N is roughly proportional to
N. A capped loop is not merely tidy; the alternative is quadratic.

### 5. The check, and where it sits

```python
    calls += 1
    print(f"TOOL CALL {calls:>2}    > ...   [{spent} tokens spent]")
    if calls >= MAX_TOOL_CALLS or spent > TOKEN_BUDGET:
        print(f"STOPPED         > cap={MAX_TOOL_CALLS} calls, budget={TOKEN_BUDGET} tokens. ...")
        break
    history.append(...)
```

The position matters. The check sits **after** the call is counted and **before**
the result is appended, so tripping the ceiling ends the turn immediately rather
than running one more model call to find out. Move it after the append and you
pay for an extra round trip on every single stop.

`calls >= MAX_TOOL_CALLS` with `>=` and `spent > TOKEN_BUDGET` with `>`: the cap
is a count of things allowed, the budget is a line you are over. Off-by-one here
is harmless but the asymmetry is intentional.

`or`, not `and` — either ceiling stops the turn on its own.

### 6. What the exit looks like

The loop has two exits. The ordinary one is content:

```python
    if not part.function_call:
        print(f"MODEL ANSWERS   > {part.text.strip()}")
        break
```

The other is the ceiling, and what it produces is *not* a model answer. The
history is abandoned mid-turn and the user is told the service could not answer.
That is deliberate: the alternative — asking the model to summarise its failure —
costs another call to say the same thing.

Which exit fires is a genuinely open question on any given run, and worth
recording in the run log. A well-behaved model may recognise after two searches
that nothing exists and refuse on its own, never reaching the cap. That is a good
outcome, and it is not something to rely on. The cap exists for the runs where it
does not happen.

---

## What to take away

- The agent decides when it is done. Your loop decides when it is not allowed to
  continue. Never let the model own both.
- Cap the steps *and* budget the tokens. One bounds looping, the other bounds
  size.
- A prompt instruction is a request; a check in the loop is a fact. Safety
  controls belong in the code.
- Every iteration re-sends the whole history, so cost grows with the square of
  the step count.
- When a ceiling trips, refuse. Do not spend another call producing a nicer
  apology.

## Related

- `01_tokens_and_the_meter.py` — where `usage_metadata` comes from.
- `04_function_call_round_trip.py` — the same loop without the ceilings.
- `13_the_reranker_and_the_floor.py` — the other way a service earns the right to
  say "nothing here".
- `demo/turn.py` — the cap in the shipping service.
- `../run_logs/07_the_cap_and_the_budget_RUN_LOG.md` — recorded runs.
