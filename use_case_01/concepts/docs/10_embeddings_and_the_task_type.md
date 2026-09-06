# 10 — Embeddings, and the task type

`../10_embeddings_and_the_task_type.py`

## Summary

Text in, 768 numbers out. The script embeds one question and four passages with
the real `gemini-embedding-001`, prints the first five numbers of the question's
vector so the thing stops being abstract, then scores every passage by cosine
similarity and sorts them.

Two smaller demonstrations follow, and they are the reason the script exists
rather than just the ranking:

1. The same sentence embedded as `RETRIEVAL_QUERY` and as `RETRIEVAL_DOCUMENT`
   does **not** produce the same vector. The task type is part of the meaning.
2. Nothing scores zero. Even "Broker commission is settled monthly in arrears"
   gets a real number against a question about water damage. A vector search
   always hands back its top k, however irrelevant — which is why a reranker with
   a floor (script 13) exists at all.

---

## Aspect by aspect

### 1. Dimensions come from the environment

```python
MODEL, DIMS = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"), int(os.getenv("EMBEDDING_DIMS", "768"))
```

`EMBEDDING_DIMS=768` in the `.env`, and it appears in three places that must
agree: the embedding call here, the `vector(768)` column in Postgres (script 11),
and the cosine arithmetic below. Change one without the others and either
Postgres rejects the insert or the maths is silently wrong.

`gemini-embedding-001` supports Matryoshka truncation — you ask for fewer
dimensions and get a shorter, still-meaningful vector. 768 is a deliberate trade:
smaller index, faster search, slightly less resolution than the full width.

### 2. The question and the passages

```python
QUESTION = "water coming through the ceiling from the flat upstairs"
PASSAGES = ["Escape of water from a neighbouring flat is covered. Excess GBP 350.",
            "Damage from gradual seepage over weeks or months is excluded.",
            "Broker commission is settled monthly in arrears.",
            "Error NW-4471 on the broker portal means the policy is mid-term adjusted."]
```

Four passages arranged as a gradient, and that arrangement is the experiment:

- **the right answer**, sharing almost no vocabulary with the question — no
  "ceiling", no "upstairs". If it ranks first, the embedding matched *meaning*.
- **a near miss** — also about water damage, also an insurance rule, but the
  opposite outcome. Semantically close, factually wrong. It should rank second,
  and that is the uncomfortable part: second place is still inside a top-3.
- **an unrelated passage** in the same domain.
- **an opaque code** — `NW-4471`. Watch this one. Embeddings are poor at exact
  identifiers, and that weakness is the entire argument for the lexical half of
  hybrid search in script 12.

### 3. Embedding, batched

```python
def embed(texts, task):
    return [e.values for e in client.models.embed_content(
        model=MODEL, contents=texts,
        config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)).embeddings]
```

`contents` takes a list, so the four passages cost one round trip. The response
carries `.embeddings`, one per input, in order — the order is the join, so it
must not be re-sorted before pairing.

`.values` is the plain list of floats.

### 4. Cosine, written out

```python
def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.dist(a, [0] * DIMS) * math.dist(b, [0] * DIMS))
```

Dot product divided by the product of the two magnitudes. `math.dist(a, [0]*DIMS)`
is the distance from the origin, which is the magnitude.

It is written out rather than imported to make the claim in the docstring
concrete: **similarity is arithmetic, not magic.** There is no model call here,
no service, no index. Two lists of floats and one division. Everything a vector
database does at scale is this, plus an index to avoid doing it a million times.

Cosine ignores magnitude and measures only direction, which is what you want when
comparing a six-word question to a twenty-word clause. It ranges −1 to 1;
embedding models in practice return a narrow positive band, which is why the
*ordering* is meaningful and the absolute value is hard to reason about.

### 5. Printing the vector

```python
print(f"{MODEL}: {len(query)} numbers for {QUESTION!r}")
print(f"  first five: {[round(v, 5) for v in query[:5]]}")
```

Worth keeping. An embedding is discussed so abstractly that people carry vague
ideas about what it is; seeing `768` and five small signed floats settles it. No
individual number means anything. Only the direction of all 768 together does.

### 6. The task type demonstration

```python
as_document = embed([QUESTION], "RETRIEVAL_DOCUMENT")[0]
print(f"\nSame sentence embedded as RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT: cosine"
      f" {cosine(query, as_document):.3f} -- the task_type is part of the meaning.")
```

Identical input text, two task types, and the cosine between the results is high
but not 1.0. The model places a question and a statement in different regions,
because a question and the passage that answers it are not paraphrases of one
another — asymmetric retrieval is exactly the job.

The practical consequence: embed documents with `RETRIEVAL_DOCUMENT` at ingest
and questions with `RETRIEVAL_QUERY` at search time, and never mix them. Getting
this wrong degrades retrieval quietly. Nothing errors, scores just get worse, and
there is no way to notice without a golden set (script 17).

Other task types exist — `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING` —
and the two used here are the retrieval pair.

### 7. The closing line

```python
print("Note that nothing here scored zero: a vector search hands back its top k, always.")
```

The most important sentence in the file. Every passage scored, including broker
commission, including the error code. Ask for the top 3 and you get 3, even when
the corpus holds nothing relevant at all.

So vector search cannot say "nothing here". It has no threshold and no notion of
absence. Something else has to supply that, which is the reranker floor in script
13 and the reason `demo/.env` carries `RERANK_FLOOR=0.3`.

---

## What to take away

- An embedding is a fixed-length list of floats. Similarity is a dot product over
  magnitudes — arithmetic you can write in one line.
- `EMBEDDING_DIMS` must agree across the embedding call, the Postgres column and
  the maths.
- Task type is part of the input. `RETRIEVAL_QUERY` for questions,
  `RETRIEVAL_DOCUMENT` for chunks, always.
- Embeddings match meaning, not tokens — and that is also their weakness: exact
  codes and identifiers retrieve poorly.
- A vector search always returns k results. It can never report that there is
  nothing to find.

## Related

- `09_a_chunk_is_a_clause.py` — what you embed matters as much as how.
- `11_pgvector_is_the_store.py` — the same arithmetic, done by Postgres.
- `12_hybrid_search_and_rrf.py` — covering the identifier weakness with lexical
  search.
- `13_the_reranker_and_the_floor.py` — supplying the "nothing here" that vector
  search cannot.
- `demo/embeddings.py` — the shipping version.
- `../run_logs/10_embeddings_and_the_task_type_RUN_LOG.md` — recorded runs.
