# 05 — The docstring is the interface

`../05_the_docstring_is_the_interface.py`

## Summary

Script 04 showed that the model never sees your function, only a declaration.
This script shows where that declaration comes from when you use ADK: **your
docstring.**

It builds the same trivial function twice, gives it a good docstring the first
time and a vague one the second, hands each to `FunctionTool`, and prints the
declaration ADK derives. The name is identical. The parameter schema is
byte-for-byte identical. The description is 590 characters against 69.

That is the whole file. It makes no model call, needs no credentials and costs
nothing — it is an inspection, not a demonstration of behaviour. What it inspects
is the exact object that would go on the wire, so the difference on screen is the
difference the model would actually see.

---

## Aspect by aspect

### 1. Two docstrings, side by side

```python
GOOD = """Search this team's own Northwind Assurance documents.

Use this for any question about policy wordings, cover, exclusions, claims handling,
underwriting appetite, broker terms, complaints procedure, error codes, timescales or
authority limits. Search first; never answer such a question from memory.

Args:
    question: The user's question, in their own words. Do not paraphrase it into keywords.

Returns:
    A dict with a "passages" list; each passage has "source_file" and "clause" (cite both
    as [source_file §clause]), "heading" and "content". An empty list means nothing matched.
"""
```

Read it as a prompt, because that is what it is. Four jobs are being done:

- **First line — what it is.** A one-line summary, so a model skimming a tool
  belt of ten tools can tell at a glance which one this is.
- **Second paragraph — when to use it.** The subject list ("policy wordings,
  cover, exclusions, claims handling, underwriting appetite, broker terms,
  complaints procedure, error codes, timescales or authority limits") exists so
  the model recognises an in-scope question it has never seen phrased that way.
  Then the order: *search first; never answer such a question from memory.* That
  sentence is the grounding rule, and it lives here rather than in the agent
  instruction because it is a fact about this tool.
- **`Args:` — how to call it.** "In their own words. Do not paraphrase it into
  keywords" is a correction for a real habit: models like to helpfully compress a
  question into search terms, which destroys the semantic signal the embedding
  search depends on.
- **`Returns:` — what to do with the result.** The return shape is described
  *and* the citation format is specified inline, `[source_file §clause]`. The
  last sentence — "An empty list means nothing matched" — is what lets the model
  distinguish a failed search from a broken tool, and so is what makes an honest
  refusal possible.

```python
VAGUE = """Looks things up.

Args:
    question: a string.

Returns:
    A dict.
"""
```

Everything true, nothing useful. This is what an ordinary, blameless Python
docstring looks like — and it is why the habit has to be unlearned here. A
docstring that would pass code review is not necessarily a usable tool
declaration.

### 2. A fresh function per docstring

```python
def make_search_tool(doc: str):
    """A fresh function per agent, exactly as demo/agent.py's make_search_tool does it.
    ADK caches the declaration per function object, so the docstring is swapped on a new one."""
    def search_knowledge_base(question: str) -> dict:
        return {"passages": []}
    search_knowledge_base.__doc__ = doc
    return search_knowledge_base
```

The closure matters, and its own docstring says why: ADK caches the derived
declaration against the function object. Mutating `__doc__` on one reused
function would print the first declaration twice and quietly prove nothing —
a silent failure that looks exactly like a successful run.

The body returns `{"passages": []}` and is never called. Only the signature and
the docstring are read. This is the point made concrete: the implementation is
irrelevant to what the model is told.

The same factory shape appears in `demo/agent.py`, where it exists for a
different reason — binding the tenant into the closure, which is script 15.

### 3. Deriving the declaration

```python
declaration = FunctionTool(make_search_tool(doc))._get_declaration()   # what is sent to Gemini
```

`FunctionTool` wraps a plain Python callable. `_get_declaration()` is private,
and it is called deliberately: the object it returns is precisely what ADK puts
on the wire. Nothing in `demo/` depends on this method; it is here so the thing
under discussion can be printed rather than described.

ADK derives three fields from three different places:

| Field | Comes from |
| --- | --- |
| `name` | the function's `__name__` |
| `parameters` | the type annotations, via a Pydantic model |
| `description` | `__doc__`, whole |

So renaming the function renames the tool, and changing an annotation changes the
schema. None of that is written by hand anywhere.

### 4. What the printed schema tells you

```
{'properties': {'question': {'title': 'Question', 'type': 'string'}},
 'required': ['question'], 'title': 'search_knowledge_baseParams', 'type': 'object'}
```

Identical across both runs, because the annotations never changed. `question: str`
became a required string; `required` is populated because the parameter has no
default. Give it one and it drops out of `required` — that is the mechanism, and
it is the ADK-flavoured version of the `required=["question"]` written by hand in
script 04.

The `title` keys are Pydantic's, harmless, and along for the ride.

Running this prints a `UserWarning` about
`FeatureName.JSON_SCHEMA_FOR_FUNC_DECL` being EXPERIMENTAL. That is ADK 2.6.3
announcing it emits `parameters_json_schema` (plain JSON Schema) rather than the
older `parameters` (`types.Schema`) form. It goes to stderr, changes nothing, and
the exit code is 0.

### 5. The number in the header

```python
print(f"\n=== {label} docstring -> declaration, {len(declaration.description)} chars of description")
```

590 against 69. A blunt measure and a useful one: it is the amount of information
the model has when deciding whether to call this tool at all. The live
consequence — vague description, model answers from memory instead of searching —
is what `TOOL_DESCRIPTION=good|vague` in `demo/.env` switches on the real agent.

---

## What to take away

- With ADK, the docstring **is** the prompt. It is not documentation that happens
  to be nearby.
- The declaration is derived from three sources: `__name__`, the annotations, and
  `__doc__`. Write all three as if the model were reading them, because it is.
- Say when to use the tool, not just what it does. Say what an empty result
  means. Specify the citation format where the return value is described.
- ADK caches a declaration per function object. Build a fresh function when the
  docstring or the binding must change.

## Related

- `04_function_call_round_trip.py` — the declaration written out by hand.
- `06_adk_agent_and_its_event_stream.py` — the same tool actually called.
- `15_no_argument_in_which_to_ask.py` — the signature as a security boundary.
- `demo/agent.py` — `make_search_tool`, in the service.
- `../run_logs/05_the_docstring_is_the_interface_RUN_LOG.md` — recorded runs.
