# 12 — Hybrid search and RRF

`../12_hybrid_search_and_rrf.py`

## Summary

Script 10 left a hole: embeddings match meaning, and an error code like
`NW-4471` has no meaning to match. Script 11 left another: `LIMIT` always returns
`LIMIT`. This script closes the first hole.

It loads five rows into Postgres with both an `embedding` column and a generated
`tsvector` column, then runs two questions through three searches each — vector,
lexical, and the two fused by Reciprocal Rank Fusion. The two questions are
chosen to pull in opposite directions. *"what does error NW-4471 mean"* is a job
for keyword search. *"water coming through the ceiling from upstairs"* is a job
for the embedding. Neither method wins both.

The fusion is by **rank**, not by score, and that is the part worth understanding.
A cosine distance and a `ts_rank` are numbers on unrelated scales; adding or
averaging them is meaningless. Their positions in a list, however, compare fine.

A third query runs on the side to show why the lexical half needs care:
`websearch_to_tsquery` ANDs every word of the question, so a full sentence
usually matches nothing at all.

## Prerequisite

```
docker compose -f ../demo/docker-compose.yml up -d
```

---

## Aspect by aspect

### 1. The corpus, built around one identifier

```python
ROWS = ["A pending mid-term adjustment blocks the quote; the portal shows NW-4471.",
        "If the broker portal shows an error, ask what the message says and retry after a minute.",
        "Portal error messages and what they mean are listed in the monthly broker bulletin index.",
        "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
        "Broker commission is settled monthly in arrears."]
```

Row 1 is the only row containing `NW-4471`. Rows 2 and 3 are the *semantic*
neighbours — they are about portal errors in general, they read like a helpful
answer, and they do not contain the code.

That is the trap. Ask an embedding "what does error NW-4471 mean" and rows 2 and
3 look excellent: they are on-topic, they use the vocabulary, they are about
errors. Row 1 mentions the code once in a sentence otherwise about mid-term
adjustments. Vector search will often rank the two generic rows above the one
row that actually answers the question — and lexical search finds row 1
instantly, because it is looking for a literal token.

### 2. The generated tsvector column

```python
conn.execute(f"""CREATE TABLE concept_chunks (id bigserial PRIMARY KEY, content text NOT NULL,
    embedding vector({DIMS}) NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED)""")
```

`GENERATED ALWAYS AS ... STORED` means Postgres maintains the column. Insert or
update `content` and `tsv` is recomputed by the database — it cannot drift, and
no application code has to remember to update it. Compare with the `embedding`
column, which the application must compute and keep in step by hand.

`to_tsvector('english', ...)` does the linguistic work: lowercasing, stemming
("settled" → "settl"), and dropping stop words. That is why the lexical half is
not merely a `LIKE`.

The insert only writes `content` and `embedding`. `tsv` is not in the column
list, because writing to a generated column is an error.

### 3. Any-term, not all-terms

```python
ANY_TERM = "replace(websearch_to_tsquery('english', %s)::text, '&', '|')::tsquery"   # demo/retrieval.py
```

This one line is the most practically useful thing in the script.

`websearch_to_tsquery('english', 'what does error NW-4471 mean')` produces
`'error' & 'nw' & '4471' & 'mean'` — every term ANDed. A row matches only if it
contains *all* of them. For a natural-language question of eight or ten words,
almost nothing ever does, and the lexical half of your hybrid search silently
returns zero rows on every query.

The fix is a hack, and an honest one: render the tsquery to text, replace `&`
with `|`, cast it back. Now any term matching is enough, and `ts_rank` sorts by
how many matched and how prominently.

The script proves the problem rather than asserting it:

```python
    all_terms = ids(conn.execute("SELECT id FROM concept_chunks WHERE tsv @@ websearch_to_tsquery('english', %s)", (question,)).fetchall())
    ...
    print(f"  lexical ALL-term   {all_terms}   <- websearch_to_tsquery ANDs every word of the question")
```

That line prints `[]` for both questions. Empty. The same code shipped in
`demo/retrieval.py`, which is why the workaround is in the demo too.

### 4. The two rankings

```python
    vector_ranked = ids(conn.execute("SELECT id FROM concept_chunks ORDER BY embedding <=> %s::vector LIMIT 3", (query,)).fetchall())
    lexical_ranked = ids(conn.execute(f"SELECT id FROM concept_chunks WHERE tsv @@ {ANY_TERM}"
                                      f" ORDER BY ts_rank(tsv, {ANY_TERM}) DESC LIMIT 3", (question, question)).fetchall())
```

Only ids are selected — the fusion works on ids, and the content is fetched once
at the end in the real implementation.

The vector query has no `WHERE`: it always returns 3 (script 11). The lexical
query has `WHERE tsv @@ ...` and therefore may return fewer, or none. That
asymmetry is real and useful — lexical search *can* say "nothing matched", vector
search cannot.

`ORDER BY ... DESC` for `ts_rank` (higher is better) against `ORDER BY ... ASC`
for `<=>` (lower is closer). Two operators, opposite directions, one more reason
not to try to combine their scores.

The query text is passed twice because `ANY_TERM` is interpolated twice, once in
the `WHERE` and once in the `ORDER BY`. The `%s` inside it stays a real
placeholder, so the *question* is still parameterised — the f-string interpolates
only the fixed SQL fragment, never user input.

### 5. Reciprocal Rank Fusion

```python
    fused = {}
    for ranked in (vector_ranked, lexical_ranked):
        for rank, row_id in enumerate(ranked, start=1):
            fused[row_id] = fused.get(row_id, 0.0) + 1.0 / (RRF_K + rank)
```

The whole algorithm, five lines. Each list contributes `1 / (k + rank)` to every
document it ranked, and the contributions are summed.

Three properties make it the default choice:

- **It never looks at a score.** Only positions. So a cosine distance and a
  `ts_rank` can be combined without normalisation, calibration, or a tuned
  weight — which is fortunate, because normalising them is not actually possible
  in any principled way.
- **It rewards agreement.** A document ranked 2nd by both methods beats a
  document ranked 1st by one and absent from the other. That is exactly the
  behaviour wanted: consensus across two different notions of relevance is the
  strongest signal available.
- **It handles absence for free.** A document only one list found still scores,
  just less. No special case.

`RRF_K = 60` is the value from the original paper and the one everyone uses. Its
job is to flatten the difference between the top few positions, so rank 1 does
not overwhelm rank 2 and 3. Larger k flattens more, smaller k sharpens. It is
almost never worth tuning.

### 6. Reading the output

Two questions, three lines of ranking each, and the interesting comparison is
between the lines.

For **`NW-4471`**, expect the lexical row to lead with row 1 and the vector row
to favour rows 2 and 3. The fused list should bring row 1 up. This is the case
that justifies the whole exercise.

For **the water question**, expect the reverse: the vector search finds row 4
despite sharing barely a word with the question, while lexical search struggles —
"water", "ceiling" and "upstairs" appear nowhere in the wording, and any-term
matching on a stop-word-stripped question may pull in unrelated rows. The fusion
keeps the right answer near the top anyway.

And `lexical ALL-term` prints `[]` on both. That empty list is a result, not a
failure of the script.

---

## What to take away

- Embeddings retrieve meaning; keyword search retrieves tokens. Codes,
  identifiers, names and product references need the second.
- Fuse by rank, never by score. Cosine distance and `ts_rank` do not share a
  scale and cannot be normalised into one.
- RRF is `1/(60+rank)` summed across methods. That is all of it.
- `websearch_to_tsquery` ANDs the question. Over natural-language questions that
  matches nothing — swap `&` for `|`.
- Let Postgres maintain the `tsvector` with a generated column; only the
  embedding needs application code.

## Related

- `10_embeddings_and_the_task_type.py` — the identifier weakness this fixes.
- `11_pgvector_is_the_store.py` — the vector half of the same table.
- `13_the_reranker_and_the_floor.py` — what happens to the fused candidates next.
- `demo/retrieval.py` — the shipping hybrid search, `ANY_TERM` and all.
- `../run_logs/12_hybrid_search_and_rrf_RUN_LOG.md` — recorded runs.
