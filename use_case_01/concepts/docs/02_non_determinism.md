# 02 — Non-determinism, and what temperature 0 does not promise

`../02_non_determinism.py`

## Summary

The script sends one fixed prompt to Gemini eight times: five calls at
`temperature=1.0`, then three at `temperature=0.0`. After each group it counts
how many *distinct* strings came back.

The high-temperature group almost always returns five different sentences. The
zero-temperature group usually returns one, and sometimes does not. That
"sometimes" is the whole point. Temperature 0 makes the model pick the
highest-probability token at each step; it does not make a distributed
floating-point service reproducible. Batching, hardware and routing all move
underneath you.

So the script exists to set an engineering rule for everything downstream:
**assert the shape of what you do not control, and the exact wording only of the
sentence you wrote yourself.** That last line is printed by the script, and it is
the rule `demo/test_acceptance.py` is written to.

---

## Aspect by aspect

### 1. Configuration

The standard preamble — see
[`04_function_call_round_trip.md`](04_function_call_round_trip.md).

### 2. One passage, one prompt, held constant

```python
PASSAGE = ("[01_escape_of_water.md §4] Escape of water from a neighbouring flat is covered."
           " The excess is GBP 350 and the claim must be notified within 30 days.")
PROMPT = ("Answer this Claims question in one sentence from the passage below, citing"
          f" [file §clause].\n\n{PASSAGE}\n\nQuestion: my upstairs neighbour's washing"
          " machine flooded my ceiling -- am I covered, and what do I pay?")
```

Everything is a module-level constant. Nothing varies between calls except the
temperature, so any difference in output is the model and only the model.

The passage carries two facts — the excess and the 30-day notification window —
and the instruction asks for one sentence. That gap is deliberate: with two facts
and one sentence, the model has to choose what to include, and different runs
choose differently. A question with a single one-word answer would hide the
effect.

The question is also phrased in a customer's words ("washing machine flooded my
ceiling") while the passage is in the wording's words ("escape of water from a
neighbouring flat"). The model has to bridge that. Nothing in the sentence
matches on keywords.

### 3. The two groups

```python
for temperature, samples in ((1.0, 5), (0.0, 3)):
```

Five samples at 1.0, three at 0.0. Five is enough to make variation obvious;
three at 0.0 is enough to show agreement without spending eight calls proving a
negative. Both numbers are pedagogic, not statistical — nobody should read a
significance claim into eight samples, and it is worth saying so when teaching
it.

```python
        reply = client.models.generate_content(
            model=MODEL, contents=PROMPT,
            config=types.GenerateContentConfig(temperature=temperature))
```

`temperature` is the only thing in the config. It scales the logits before
sampling: high temperature flattens the distribution and lets unlikely tokens
through, zero collapses it to always taking the most likely token.

### 4. Counting distinct answers

```python
        answers.append(reply.text.strip())
    print(f"  -> {len(set(answers))} distinct answer(s) out of {samples}")
```

`set()` over the stripped strings — an exact-string comparison, which is the
harshest possible test and the right one here. Two answers that differ by a comma
are two answers as far as a regex, a snapshot test or a string assertion is
concerned, and those are exactly the things this script is warning you about.

The count is the whole result. At 1.0 you should expect 5 of 5, or 4 of 5. At 0.0
you should expect 1 of 3 — and if you ever see 2 of 3, that is not a bug in the
script, it is the lesson landing harder than usual. Keep that run in the log.

### 5. The closing rule

```python
print("\nEvery run is a fresh sample. Assert the shape of what you do not control,"
      "\nand the exact wording only of the sentence you wrote yourself.")
```

The distinction matters and it runs through the whole use case. You do not
control the model's prose, so test it structurally: that a citation is present,
that it resolves, that the answer is under N sentences, that the JSON parses,
that the right passage was retrieved. You *do* control the refusal string —
`"That is not in the documents."` is a constant in `demo/guardrails.py`, not
something the model composes — so that one string can be asserted exactly.
Scripts 03, 16 and 17 are each an instance of this rule.

---

## What to take away

- Every call is a fresh sample from a distribution. There is no cache and no
  memory between them.
- `temperature=0` means greedy decoding, not reproducibility. Nothing in a
  distributed inference service guarantees bit-identical output.
- Therefore: never snapshot-test model prose, never regex a number out of a
  sentence, never assert equality on generated text.
- Assert structure instead — and assert exact strings only for text your own code
  wrote.

## Related

- `03_structured_output.py` — the fix: make the shape enforceable by the API.
- `16_a_citation_you_can_open.py` — asserting structure on the way out.
- `17_the_golden_set.py` — measuring quality when the output varies.
- `demo/test_acceptance.py` — the rule, applied.
- `../run_logs/02_non_determinism_RUN_LOG.md` — recorded runs.
