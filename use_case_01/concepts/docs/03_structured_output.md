# 03 — Structured output: ask for data, not prose

`../03_structured_output.py`

## Summary

The script gives the model the same job twice — score three passages 0.0–1.0 for
how well each answers a question — and asks for the result two ways. First as
free text, then with a `response_schema` attached.

The free-form reply is read back with a regular expression. The
schema-constrained reply is read back with `json.loads`. Both lines print what
they extracted, and the contrast is the lesson: the regex is a guess about
formatting that the model never agreed to, while the schema is a constraint the
API enforces during decoding.

This is the direct sequel to script 02. Non-determinism is the problem; a
response schema is the answer whenever the thing you want back is data rather
than prose. The job used here is not arbitrary — it is exactly the reranking call
`demo/rerank.py` makes in production, so the schema on screen is the schema that
ships.

---

## Aspect by aspect

### 1. Configuration

The standard preamble — see
[`04_function_call_round_trip.md`](04_function_call_round_trip.md).

### 2. The job

```python
PASSAGES = {1: "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
            2: "Broker commission is settled monthly in arrears.",
            3: "Damage from gradual seepage over weeks or months is excluded."}
PROMPT = ("Score each passage 0.0-1.0 for how well it answers the question."
          " Question: is water from the flat above covered?\n"
          + "\n".join(f"[{i}] {t}" for i, t in PASSAGES.items()))
```

Three passages: one that answers the question, one that is irrelevant, one that
is topically close but says the opposite. Each is prefixed with a small integer
id, and that id is the join key — the model returns ids, and the caller maps them
back to passages. Sending the ids rather than the texts back keeps the reply
short, which is the cheap half of the bill.

### 3. The schema

```python
SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(
    type=types.Type.OBJECT, required=["id", "score"], properties={
        "id": types.Schema(type=types.Type.INTEGER),
        "score": types.Schema(type=types.Type.NUMBER)}))
```

An array of objects, each with a required integer `id` and a required number
`score`. That is all a reranker needs.

`required=["id", "score"]` is what makes the parse safe. Without it, a returned
object may legitimately omit a field, and `r["score"]` raises `KeyError` at the
worst moment. Declaring a field is not the same as requiring it.

Note the types: `INTEGER` for the id and `NUMBER` for the score. Ask for a
`STRING` score and you have handed the parsing problem back to yourself.

### 4. The free-form call

```python
prose = client.models.generate_content(model=MODEL, contents=PROMPT + "\nReply as text.")
print("=== free-form reply, verbatim\n" + prose.text.strip())
print("  regex over it ->", dict(re.findall(r"\[?(\d)\]?[^0-9]{0,20}(0\.\d+)", prose.text)))
```

The reply is printed verbatim first, deliberately, so you can see what the regex
is up against — usually a friendly sentence per passage, sometimes a markdown
table, sometimes a preamble like "Here are the scores:".

The regex is worth reading closely because it is a fair attempt, not a straw man:
find a digit, optionally bracketed, then up to twenty non-digit characters, then
something that looks like `0.x`. It works often. It fails silently in ways that
matter:

- a score written as `1.0` never matches `0\.\d+` — the best passage is the one
  it drops
- a score written as `95%` or `0,8` does not match
- `[^0-9]{0,20}` will happily bridge across passages if the model is terse
- `dict()` over the pairs keeps the last match for a repeated id, silently
- the keys are **strings**, because `re.findall` returns strings — so the result
  is `{'1': '0.9'}` and not `{1: 0.9}`, which will not join against
  `PASSAGES` without a cast

None of these raise. They produce a plausible dict with the wrong contents, and
that is worse than an exception.

### 5. The schema-constrained call

```python
typed = client.models.generate_content(
    model=MODEL, contents=PROMPT,
    config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                       response_schema=SCHEMA))
print("  json.loads   ->", {r["id"]: r["score"] for r in json.loads(typed.text)})
```

Three settings, all three needed:

- **`response_mime_type="application/json"`** — the reply is JSON and nothing
  else. No prose wrapper, no ```json fence to strip.
- **`response_schema=SCHEMA`** — constrained decoding. The model is restricted to
  tokens that keep the output valid against the schema, so this is not a request
  in the prompt that the model may ignore; it is enforced at generation time.
  Nothing to retry, nothing to repair.
- **`temperature=0`** — the scores are a judgement, not a creative act. Script 02
  applies: this makes the scoring as stable as it can be made, without promising
  it is identical run to run.

The parse is then one line with no error handling, and it is honest — the ids
really are integers and the scores really are floats, so the dict comprehension
joins straight back to `PASSAGES`.

### 6. What the output shows

The free-form and schema-constrained runs usually agree on the *ranking*. The
model is equally capable both ways. What differs is whether your code can rely on
reading it. That is the entire argument, and it is worth stating plainly when
teaching: this is not about making the model smarter, it is about removing a
failure mode from the caller.

---

## What to take away

- If the output feeds code, ask for data. If it feeds a human, ask for prose.
  Never parse prose that a schema could have given you.
- `response_schema` is enforced during decoding, not requested in the prompt.
- `required` is what makes the parse safe; declaring a property does not.
- A regex over model output fails by returning something wrong, not by raising.
  That is why it is dangerous.
- Small integer ids in, small integer ids out — keep the expensive tokens on the
  input side.

## Related

- `02_non_determinism.py` — the problem this solves.
- `13_the_reranker_and_the_floor.py` — this exact schema, doing its real job.
- `demo/rerank.py` — the shipping version.
- `../run_logs/03_structured_output_RUN_LOG.md` — recorded runs.
