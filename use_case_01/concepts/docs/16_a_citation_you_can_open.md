# 16 — A citation you can open

`../16_a_citation_you_can_open.py`

## Summary

Three prompts, three real answers, one checker.

The first run attaches the passage and instructs the model to cite. The second
attaches nothing but keeps the grounding rule and the exact refusal string. The
third removes the rule as well and simply says "You are an insurance expert."

Every answer is then put through `check()`, which is `demo/guardrails.check_answer`
in miniature. It passes an answer only if it is the exact refusal string, or if
every citation in it **resolves against the documents on disk**.

That last part is the title. It is not enough that an answer looks cited. A
citation that points at a file or clause that does not exist is worse than no
citation, because it manufactures the appearance of grounding. The check runs
against `DOCUMENTS`, not against what the retriever returned, so a model
inventing a plausible filename is caught.

The third run is the one to watch. With no passages and no rule, the model
answers fluently and confidently about UK insurance from its training data. It is
not wrong, exactly. It is simply not *your* wording, and there is no way for a
reader to tell.

---

## Aspect by aspect

### 1. The documents are the ground truth

```python
DOCUMENTS = {("01_escape_of_water.md", "4"): "Escape of water from a neighbouring flat is covered. Excess GBP 350."}
```

One entry, keyed by `(file, clause)` — the pair a citation names. In the service
this is the corpus on disk.

Checking against the corpus rather than against the retrieved passages is a
deliberate choice. Retrieved passages tell you what the model *was given*;
the corpus tells you whether the citation can be *opened*. Only the second is
what a compliance reviewer will do.

### 2. The refusal is a constant

```python
REFUSAL = "That is not in the documents."                              # demo/guardrails.py, verbatim
```

Script 02's rule, made concrete. This string is not composed by the model — it is
written in Python, instructed verbatim, and compared verbatim. That is the one
piece of output text an exact-equality assertion is allowed to touch.

### 3. The citation pattern

```python
CITATION = re.compile(r"[\[(]\s*(?P<file>[\w\-.]+\.md)\s*[,;]?\s*(?:§|clause\s+)\s*(?P<clause>[0-9.]+)\s*[\])]")
```

This is the one place a regex over model output is the right tool, and it is
worth being clear why: script 03 rejected regexes for *extracting data the model
was asked to produce*. Here the regex is a **validator applied to prose** — the
answer is genuinely prose, prose is what the user reads, and the citation must be
found inside it.

The pattern is deliberately tolerant, because the model's formatting will drift:

- `[\[(]` … `[\])]` — square brackets or parentheses.
- `\s*` at every join — whitespace anywhere.
- `[,;]?` — an optional separator, so `[01_escape_of_water.md, §4]` matches.
- `(?:§|clause\s+)` — the section sign or the word "clause".
- `[0-9.]+` — dotted clause numbers like `4.2`.
- Named groups, so the extraction reads as `m.group("file")` rather than
  `m.group(1)`.

Tolerance is the correct bias for a validator: a strict pattern rejects a good
answer over a comma, and the resolution check below is what catches the real
failures.

### 4. The check

```python
def check(answer):
    if answer.strip() == REFUSAL:
        return "PASS (honest refusal)"
    found = [(m.group("file"), m.group("clause")) for m in CITATION.finditer(answer)]
    if not found:
        return "BLOCKED (no citation at all)"
    unresolved = [c for c in found if c not in DOCUMENTS]
    return f"BLOCKED (citation does not open: {unresolved})" if unresolved else f"PASS (opens: {found})"
```

Four outcomes, in order, and the order encodes the policy.

**Refusal first.** An honest refusal is a success, not a failure. If this check
came second, a refusal containing no citation would be blocked as ungrounded —
exactly backwards. A service that is not allowed to say "I don't know" will
invent something instead.

**No citation at all → BLOCKED.** Not warned, not flagged. The answer does not
reach the user. This is the third run's outcome.

**Any unresolvable citation → BLOCKED.** `finditer` finds every citation and the
test is over all of them — one bad citation blocks the answer even if three
others are fine. Strict, and right: a reader who spot-checks one citation and
finds it good will trust the rest.

**Otherwise PASS**, and the resolved pairs are reported.

Note the verdict is binary. There is no "low confidence" state, because a
confidence score on an answer nobody can verify is just a second thing nobody can
verify.

### 5. The three runs

```python
RUNS = [("passages attached", GROUNDED + "\n\nPassages:\n[01_escape_of_water.md §4] " + ...),
        ("no passages, grounded instruction", GROUNDED + "\n\nPassages:\n(none)"),
        ("no passages, no grounding rule", "You are an insurance expert. Answer in three sentences.")]
```

A controlled sequence — each run removes one thing.

**Run 1** is the working service. Passage present, citation format specified,
refusal string specified. Expect a short cited answer and `PASS (opens: ...)`.

**Run 2** is the honest-failure case, and the most important one to get right.
`Passages:\n(none)` is what the pipeline produces when the reranker floor drops
everything (script 13). The instruction gives the model an approved way to fail,
quoted exactly. Expect the refusal string and `PASS (honest refusal)`.

The `GROUNDED` prompt is what makes that possible:

```python
GROUNDED = ("Answer only from the passages. Cite every claim inline as [source_file §clause]."
            f' If the passages do not answer it, reply with exactly: "{REFUSAL}"')
```

Three instructions: ground, cite in this format, and here is the exact sentence
to use when you cannot. The refusal string is interpolated from the constant, so
the prompt and the comparison can never drift apart.

**Run 3** is an ordinary chatbot. No passages, no grounding rule, just a persona.
The answer will be fluent, plausible and probably broadly accurate about UK
insurance in general — and it will carry no citation, so `check` blocks it. The
teaching point is the gap between how good the answer *reads* and what the
guardrail *decides*. Every instinct in the room will say the third answer is
fine.

### 6. Opening the citation

```python
    if DOCUMENTS.get(("01_escape_of_water.md", "4")) and "01_escape_of_water.md" in reply.text:
        print(f"  -> opened [01_escape_of_water.md §4]: {DOCUMENTS[('01_escape_of_water.md', '4')]}")
```

The last flourish: having validated that the citation resolves, print what it
resolves *to*. That is what "a citation you can open" means — the reader can go
from the answer to the source text in one step, and check it themselves.

In the service this is what the UI does with the citation, and it is the feature
that makes the whole system reviewable by a compliance function rather than
trusted on faith.

---

## What to take away

- Check the answer on the way out, not just the passages on the way in.
- A citation must **resolve against the corpus**. Validate against the documents,
  not against what the retriever happened to return.
- Check the refusal first. A service that cannot say "I don't know" will invent
  something.
- Any unresolvable citation blocks the whole answer.
- The exact refusal string lives in code and is interpolated into the prompt, so
  the two cannot drift.
- A confident, fluent, uncited answer is the failure mode this exists to catch —
  and it is the one that looks best.

## Related

- `02_non_determinism.py` — assert structure, and exact wording only for text you
  wrote.
- `09_a_chunk_is_a_clause.py` — where the clause number in the citation comes
  from.
- `13_the_reranker_and_the_floor.py` — how "no passages" happens legitimately.
- `18_streaming_and_the_late_verdict.py` — running this check when the answer has
  already been shown.
- `demo/guardrails.py` — the shipping checker.
- `../run_logs/16_a_citation_you_can_open_RUN_LOG.md` — recorded runs.
