# 13 — The reranker and the floor

`../13_the_reranker_and_the_floor.py`

## Summary

Retrieval hands back its top k whether or not any of it is relevant — script 10
said so, script 11 demonstrated it in SQL. This script supplies the missing
judgement.

Four candidate passages are scored 0.0–1.0 by Gemini against a question, using
the schema from script 03. Anything below `RERANK_FLOOR` is dropped. The same
four candidates are then scored against a second question that the corpus cannot
answer — *"does the policy cover a tropical fish tank?"* — and this time
everything falls below the floor and nothing survives.

That empty list is the point. It is the moment retrieval becomes able to say
**nothing here**, which is the precondition for an honest refusal. Without it,
the model is handed four irrelevant passages and a question, and the most likely
outcome is a confident answer assembled from whatever was closest.

The reranker costs one extra model call per question. The floor is what you get
for it.

---

## Aspect by aspect

### 1. The floor is configuration

```python
FLOOR = float(os.getenv("RERANK_FLOOR", "0.3"))
```

`RERANK_FLOOR=0.3` in the `.env`, alongside `RERANK=on`, `TOP_K=5` and
`RERANK_CANDIDATES=12`. Those four values are the retrieval tuning surface, and
they belong in configuration precisely because they need to be moved and
measured — which is script 17.

0.3 is low, and deliberately so. It is not "this passage answers the question",
it is "this passage is worth the model's attention". Raise it and the service
refuses more often; lower it and more noise reaches the window. There is no
correct value in the abstract, only a value measured against a golden set.

### 2. The candidates

```python
CANDIDATES = {1: "The standard buildings excess is GBP 250.",
              2: "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
              3: "Damage from gradual seepage over weeks or months is excluded.",
              4: "Broker commission is settled monthly in arrears."}
```

This is what hybrid search would have returned: the right answer at position 2
rather than 1, a plausible distractor at 1 (an excess figure — the right *kind*
of fact, the wrong one), a topical near-miss at 3, and pure noise at 4.

Passage 1 is the interesting one. Ask "what is the excess?" and a keyword search
loves it. It is wrong here, and only judgement separates it from passage 2.

Small integer ids again, as in script 03 — cheap to send, cheap to return, easy
to join back.

### 3. The schema, verbatim from the demo

```python
SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(          # demo/rerank.py, verbatim
    type=types.Type.OBJECT, required=["id", "score"], properties={
        "id": types.Schema(type=types.Type.INTEGER), "score": types.Schema(type=types.Type.NUMBER)}))
```

The same schema as script 03, and the comment says it is the shipping one. This
is where the structured-output lesson pays off: the scores go straight into
arithmetic — a comparison against `FLOOR` — so a regex over prose would be
putting a guessed number in charge of whether the service answers or refuses.

### 4. The rerank call

```python
    prompt = (f"You are ranking retrieved passages for relevance to one question.\n\nQuestion: {question}\n\n"
              + "\n".join(f"[{i}] {t}" for i, t in CANDIDATES.items())
              + "\n\nScore each passage 0.0 (irrelevant) to 1.0 (directly answers the question).")
    reply = client.models.generate_content(model=MODEL, contents=prompt, config=types.GenerateContentConfig(
        temperature=0, response_mime_type="application/json", response_schema=SCHEMA))
    return {int(r["id"]): float(r["score"]) for r in json.loads(reply.text)}
```

The prompt anchors both ends of the scale — 0.0 is *irrelevant*, 1.0 is *directly
answers the question* — because an unanchored 0-to-1 scale drifts, and the floor
comparison depends on the scale meaning the same thing every run.

All candidates go in one call, not one call each. That matters twice over: it is
one round trip instead of four, and the model scores them *relatively*, seeing
its other options. A passage scored in isolation tends to look better than it is.

`temperature=0`, as in script 03 — this is a judgement, not composition.

`int(...)` and `float(...)` around values the schema already types: harmless
belt-and-braces, and it makes the dict keys unambiguous integers for the join
back to `CANDIDATES`.

Why a general model rather than a dedicated cross-encoder reranker? Because it is
one API you already have, with no extra service to run — the right trade for this
corpus. A dedicated reranker is cheaper and faster at scale, and swapping it in
is a change to `demo/rerank.py` alone.

### 5. The floor, applied

```python
    kept = [i for i in sorted(scores, key=scores.get, reverse=True) if scores[i] >= FLOOR]
```

Sort by score descending, then filter. Two operations that are usually conflated
and are not the same thing: sorting decides the order the model reads them in,
filtering decides whether they reach the model at all.

`>=` — a passage exactly on the floor survives.

`sorted(scores, key=scores.get, ...)` iterates the dict's keys and looks each one
up. Compact, and it is the same idiom used in scripts 12 and 17.

### 6. The two questions

```python
for question in ("my upstairs neighbour flooded my ceiling -- am I covered?",
                 "does the policy cover a tropical fish tank?"):
```

The first is answerable. Expect passage 2 to score high, passage 1 and 3 somewhere
in the middle, passage 4 near zero — and one or two passages to survive. Note what
happened to passage 1: retrieval ranked it first, the reranker did not. That
reordering is the cheap half of the value.

The second is not answerable. All four should score near zero and the printed
line becomes:

```
  -> 0 passage(s) survive the floor. Retrieval can now say: nothing here.
```

That is the expensive half of the value, and the reason the extra call is
justified. Compare with script 07, where the model was told to keep searching
until it found something and had no way to conclude that nothing existed.

The conditional in the f-string only prints the sentence when `kept` is empty,
which keeps the successful case quiet.

### 7. Where this sits in the pipeline

Hybrid search (script 12) returns `RERANK_CANDIDATES=12`. The reranker scores
those twelve, drops everything under the floor, and passes at most `TOP_K=5` to
the model. So the pipeline widens then narrows: cheap recall first, expensive
precision second, and only the survivors cost context-window tokens (script 01).

Turning `RERANK=off` removes the second stage entirely and hands the raw top-k
straight through. That switch exists so the two configurations can be scored
against each other — which is script 17.

---

## What to take away

- Retrieval ranks. It does not judge. The reranker judges.
- A floor is what turns a ranked list into a possibly-empty list, and an empty
  list is what makes an honest refusal possible.
- Score all candidates in one call so they are judged against each other, and
  anchor both ends of the scale in the prompt.
- Use a response schema — the score drives a branch in your code, so it must
  parse.
- The floor is a tuned number. Configuration, not a constant, and measured
  against a golden set.

## Related

- `03_structured_output.py` — the schema, introduced.
- `10_embeddings_and_the_task_type.py`, `11_pgvector_is_the_store.py` — why
  retrieval cannot refuse.
- `16_a_citation_you_can_open.py` — the refusal, once the passages are empty.
- `17_the_golden_set.py` — measuring `RERANK=off` against `RERANK=on`.
- `demo/rerank.py` — the shipping reranker.
- `../run_logs/13_the_reranker_and_the_floor_RUN_LOG.md` — recorded runs.
