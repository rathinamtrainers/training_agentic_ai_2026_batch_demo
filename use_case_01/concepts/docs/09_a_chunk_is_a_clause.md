# 09 — A chunk is a clause

`../09_a_chunk_is_a_clause.py`

## Summary

One short policy wording, cut two ways. The first cut follows the document's own
structure — one chunk per numbered clause. The second cut ignores the document
entirely and takes 200 characters at a time. Both sets are embedded with the real
`gemini-embedding-001`, both are scored by cosine against one question, and both
results are printed with the citation each chunk would produce.

The clause cut gives two chunks, each citable as `[wording.md §3]` or
`[wording.md §4]`. The character cut gives chunks that straddle the boundary, and
the script counts them — those chunks cite `§3+4`, which is to say they cite
nothing a reader can open.

The title is the rule: **cut on the clause boundary, because a clause is what a
citation points at.** Chunking is usually taught as a retrieval-quality knob.
Here it is taught as a citation problem, because in a grounded answer service an
answer nobody can verify has failed regardless of how well it retrieved.

---

## Aspect by aspect

### 1. The document

```python
DOC = """## 3. Gradual seepage
Damage caused by water that has escaped gradually over a period of weeks or months from a
fixed water system is not covered, however it is discovered.
## 4. Escape of water from a neighbouring property
Damage caused by water escaping from a neighbouring flat is covered in full, including the
cost of tracing and accessing the leak. The excess is GBP 350."""
```

Two clauses that are adjacent, similar in vocabulary, and **opposite in
outcome**. One excludes, the other covers, and both are about water escaping.

That adjacency is the trap being demonstrated. A chunk that spans the boundary
contains "is not covered" and "is covered in full" in the same breath. Retrieval
may still rank it highly — the words all match — and the model is then handed a
passage that contradicts itself, with a citation that points at two clauses at
once.

The question is put in a customer's words, not the wording's:

```python
QUESTION = "my upstairs neighbour's washing machine flooded my ceiling -- is that covered?"
```

No keyword overlap to lean on. This has to work on meaning.

### 2. The clause cut

```python
starts = [(m.group(1), m.start()) for m in re.finditer(r"^## (\d+)\.", DOC, re.M)]
spans = [(c, s, starts[i + 1][1] if i + 1 < len(starts) else len(DOC)) for i, (c, s) in enumerate(starts)]
clause_cut = [(c, DOC[s:e].strip()) for c, s, e in spans]                          # demo/chunking.py
```

Three lines, and the shape is worth reading slowly.

`re.finditer(r"^## (\d+)\.", DOC, re.M)` finds every clause heading and captures
its number. `re.M` makes `^` match at each line start rather than only at the
start of the string — without it, only the first heading is found and the whole
document becomes one chunk.

`spans` turns a list of start positions into start/end pairs: each clause runs
until the next heading begins, and the last runs to the end of the document. So
there are no gaps and no overlap — every character of the source belongs to
exactly one chunk.

The clause number is carried alongside the text from the very first step. That is
what makes `[wording.md §4]` possible later. Retrofitting a clause number onto a
chunk after the fact is guesswork; capturing it at cut time is free.

This mirrors `demo/chunking.py`, which does the same thing over the real corpus
with headings carried through as well.

### 3. The character cut

```python
window_cut = [("+".join(c for c, s, e in spans if s < i + 200 and e > i), DOC[i:i + 200].strip())
              for i in range(0, len(DOC), 200)]                                    # every 200 characters
```

`DOC[i:i+200]` for `i` stepping by 200 — the naive chunker everyone writes first,
and the default in a good many tutorials. Fast, structure-blind.

The interesting half is the label. For each window, it collects every clause that
*overlaps* it — the standard interval-overlap test, `span.start < window.end and
span.end > window.start` — and joins them with `+`. So a window living entirely
inside clause 4 is labelled `4`, and a window spanning the boundary is labelled
`3+4`.

That label is the citation this chunk could honestly produce. `§3+4` is not a
citation. It is an admission.

### 4. Embedding, with the right task types

```python
def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

query = embed([QUESTION], "RETRIEVAL_QUERY")[0]
```

`RETRIEVAL_QUERY` for the question, `RETRIEVAL_DOCUMENT` for the chunks. Not
interchangeable — script 10 measures how far apart the same sentence lands under
the two task types.

`contents` takes a list, so all the chunks of one cut are embedded in a single
call. Batching matters: it is one round trip instead of N.

```python
cosine = lambda v: sum(x * y for x, y in zip(query, v)) / (math.dist(query, [0] * DIMS) * math.dist(v, [0] * DIMS))
```

Cosine similarity written out: dot product over the product of the magnitudes.
`math.dist(v, [0]*DIMS)` is the Euclidean distance from the origin, which is the
vector's magnitude. Nothing clever, and deliberately un-abstracted — no library
call to hide behind. Script 10 makes the same point at more length.

### 5. Reading the output

```python
    print(f"\n=== {label}: {len(chunks)} chunks,"
          f" {sum('+' in c for c, _ in chunks)} of them straddling a clause boundary")
```

The header line carries the headline: how many chunks, and how many of them are
uncitable. `sum('+' in c ...)` counts labels containing a `+`, which is exactly
the straddling set.

Then each chunk is printed with its score and the citation it would emit. Two
things to watch when running it live:

- The **clause cut**'s top hit is clause 4, and the exclusion in clause 3 scores
  lower. Both are citable. A model handed the top chunk can answer and cite it.
- The **character cut** produces at least one straddling chunk, and it often
  scores *well* — it contains both clauses, so it matches more of the question's
  vocabulary. High score, useless citation, contradictory content. Retrieval
  metrics would call that a success.

Note also that the two cuts produce different numbers of chunks from the same
document, so the token cost of attaching "the top 3" differs between them. The
chunker sets the bill as much as `TOP_K` does (script 01).

---

## What to take away

- Chunk on the document's own boundaries — clause, section, heading — not on a
  character count.
- Carry the citation metadata (source file, clause, heading) from the moment of
  the cut. It cannot be recovered later.
- A chunk that spans two clauses cites neither, and may contain a rule and its
  exception together.
- A high similarity score is not the goal. A citation the reader can open is.
- Query and document embeddings use different task types.

## Related

- `10_embeddings_and_the_task_type.py` — what the vectors are and why task type
  matters.
- `16_a_citation_you_can_open.py` — the other end: checking the citation resolves.
- `demo/chunking.py` — the clause cut over the real corpus.
- `../run_logs/09_a_chunk_is_a_clause_RUN_LOG.md` — recorded runs.
