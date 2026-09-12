# Demo 2 — Tools

Demo 1's tutor could only talk. This one can act.

It is the *same* agent: `tools_agent.py` imports `tutor` from
[`../adk_01_core/core_agent.py`](../adk_01_core/core_agent.py), reuses its model
and description, extends its instruction by one paragraph, and adds one new
argument — `tools`. Importing demo 1 is also what configures Vertex AI, so the
authentication story does not change.

| Concept | Where to look in `tools_agent.py` |
|---|---|
| Function tool | `look_up_concept` — a plain function, no decorator |
| Schema inference | its type hints and docstring, which become what the model sees |
| `ToolContext` | `mark_covered`, which writes to session state |
| Tool events | the `CALL` / `REPLY` lines printed by `describe()` |

## Before you run it

Same as demo 1 — Vertex AI with Application Default Credentials:

Install the dependencies once, from the repo root:

```
pip install -r requirements.txt
```

Then authenticate to Vertex AI:

```
gcloud auth application-default login
```

## Run it

```
python adk_02_tools/tools_agent.py
python adk_02_tools/tools_agent.py "What is an Event in ADK?"
```

## What to point at in class

- **The docstring is not a comment.** It is the text the model reads when
  deciding whether to call the tool. Rewrite it vaguely and the tool stops
  getting called.
- **We never call the tool.** The `CALL` and `REPLY` lines in the output are the
  runner doing the round trip. Our code only prints them.
- **`tool_context` is invisible to the model.** ADK strips it from the schema and
  injects it. The model cannot pass it and cannot fake it.
- **The tool fixes demo 1's wrong answer.** In demo 1 the model invented a list
  of "six core ADK building blocks" from memory. Here it must look them up.
- **Exact-match lookup is brittle.** Ask for "the description field" instead of
  "description" and `look_up_concept` returns `not_found`. Worth demonstrating
  live — it is the honest reason production tools do fuzzy matching.
- **The model chooses badly sometimes.** Asked "what have I covered so far?", it
  calls `mark_covered` again rather than reading state, because we never gave it
  a read-only tool. Missing tools get substituted, not requested.
