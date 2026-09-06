# 17 — The golden set

`../17_the_golden_set.py`

## Summary

Every script so far has argued that some choice is better. This one turns the
argument into a number.

Three questions are labelled by hand with the single corpus row that answers each
— that pairing is the golden set, and a human wrote it. The script then runs the
retrieval pipeline twice over the same five-row corpus: once with the reranker
off, once with it on. For each question it computes **context precision** — the
fraction of the passages handed to the model that are the golden one — and prints
the mean across the three questions.

Two configurations, one number each. That is the deliverable.

The important property is stated in the title line: the number has to be able to
**move**. A metric that reads 1.00 for every configuration you try is not
measuring anything. With `TOP_K=3` and one correct row per question, the ceiling
without reranking is 1/3 ≈ 0.33 — so there is room above it for the reranker to
demonstrate something, or to fail to.

---

## Aspect by aspect

### 1. The labels are human, and that is the expensive part

```python
GOLDEN = [("my neighbour's washing machine flooded my ceiling -- covered?", 1),   # labelled by a human:
          ("how long do we have to send a final complaint response?", 4),         # the row that answers it
          ("what excess applies to a standard buildings claim?", 3)]
```

Three pairs of (question, correct row id). No model produced these. Someone read
the corpus and decided.

That is why golden sets are small and why they are worth their cost. Three
questions is a toy; thirty to a hundred, written by someone who knows the domain,
is a real one. The questions are also written the way users write them — the
first shares no vocabulary at all with the row that answers it — so the set tests
retrieval rather than string matching.

The three questions are chosen to stress different things: one needs semantic
matching, one is straightforward, and one — "what excess applies to a standard
buildings claim?" — has a *near-duplicate distractor* in row 1, which also
mentions an excess. That third question is where the reranker earns or loses its
keep.

### 2. The pipeline, in miniature

```python
stored = dict(zip(CORPUS, embed(list(CORPUS.values()), "RETRIEVAL_DOCUMENT")))
...
        query = embed([question], "RETRIEVAL_QUERY")[0]
        ranked = sorted(stored, key=lambda i: -sum(x * y for x, y in zip(query, stored[i])))[:TOP_K]
```

The corpus is embedded once, outside both loops, and reused. Only the questions
are re-embedded per configuration.

The ranking is a dot product, sorted descending via negation, truncated to
`TOP_K=3`. Note it is a raw dot product rather than the full cosine of script 10
— the magnitudes are omitted. For *ranking one query against many documents* that
is usually harmless, since the query's magnitude is a constant factor across all
candidates and these embeddings are near-normalised. It is a shortcut, and worth
naming as one rather than presenting as equivalent.

### 3. The reranker, with the floor

```python
def rerank(question, ids):
    ...
    return [i for i in sorted(ids, key=lambda i: -scores[i]) if scores[i] >= FLOOR]
```

Script 13's reranker, reduced to its essentials: score the candidates in one
schema-constrained call at `temperature=0`, sort, drop anything under
`RERANK_FLOOR`.

Two things it can do to the result, and both show up in the metric. It can
**reorder** — pulling the golden row above a distractor. And it can **shorten** —
dropping candidates below the floor, which raises precision by removing
denominators. The second effect is the larger one here.

### 4. Context precision

```python
        precision.append(hits.count(golden) / len(hits) if hits else 0.0)
```

Of the passages actually handed to the model, what fraction is the golden one.

The arithmetic is worth walking through, because it is what makes the two
configurations comparable:

- **RERANK=off** always hands over 3 passages. If the golden row is among them,
  precision is 1/3 ≈ 0.33; if not, 0.00. So the best possible mean is 0.33.
- **RERANK=on** hands over however many survive the floor. If only the golden row
  survives, precision is 1/1 = 1.00. If two survive and one is golden, 0.50.

So the metric rewards *not sending noise*, which is precisely the behaviour being
argued for — every dropped passage is tokens saved (script 01) and one less
opportunity for the model to ground on the wrong clause.

`if hits else 0.0` handles the case where the floor drops everything. Scoring an
empty result as 0.0 is a choice, and a debatable one: refusing to answer a
question the corpus *can* answer is a failure, so zero is right here — but it
means a floor set too high is punished by this metric, which is exactly what you
want it to tell you.

Context precision is one of the RAGAS metrics, and `demo/eval/run_ragas.py` runs
the full set properly. This script implements the one metric by hand so the
arithmetic is visible rather than delegated.

### 5. The comparison harness

```python
for label, rerank_on in (("RERANK=off", False), ("RERANK=on", True)):
```

The whole point of the structure: the same golden set, the same corpus, the same
embeddings, one flag. Everything else is held constant, so the difference between
the two printed means is attributable to the reranker.

That flag is real configuration — `RERANK=on` in `demo/.env` — so what is being
measured is a switch someone can actually throw in production, not a hypothetical.

```python
        print(f"  golden [{golden}]  handed to the model {hits}  context precision {precision[-1]:.2f}")
```

Per-question output before the mean, and it matters. A mean hides which question
regressed. When a configuration change moves the average by 0.1, the useful
question is always *which one broke*, and only the per-row line answers it.

### 6. Reading the result honestly

Expect `RERANK=off` to land at or near 0.33 and `RERANK=on` to land considerably
higher. Two cautions to state in the room:

**Three questions is not a measurement.** One question changing outcome moves the
mean by 0.33. The structure is the lesson; the number needs a real set behind it
before anyone should act on it.

**The reranker is a model call, so the number itself varies.** Script 02 applies:
run it twice and the mean may differ. A golden set does not remove
non-determinism, it makes non-determinism measurable — which is the honest
version of the claim, and why an acceptance threshold should be a band rather
than an exact figure.

---

## What to take away

- "Retrieval feels better" is not a claim you can act on. Label a set, pick a
  metric, print a number.
- The labels are human work. That cost is the price of being able to change
  anything with confidence.
- Choose a metric that can move. If every configuration scores 1.00, measure
  something else.
- Change one variable and hold the rest constant, using the real configuration
  switch.
- Print per-question results, not just the mean — the mean hides the regression.
- The metric is itself sampled from a distribution. Report a band, not a point.

## Related

- `02_non_determinism.py` — why the metric wobbles.
- `10_embeddings_and_the_task_type.py` — the retrieval being measured.
- `13_the_reranker_and_the_floor.py` — the configuration under test.
- `demo/eval/` — the full RAGAS run.
- `demo/ACCEPTANCE.md` — the thresholds this feeds.
- `../run_logs/17_the_golden_set_RUN_LOG.md` — recorded runs.
