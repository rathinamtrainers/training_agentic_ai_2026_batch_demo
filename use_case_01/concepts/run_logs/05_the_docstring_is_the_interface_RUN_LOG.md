# Run log — 05_the_docstring_is_the_interface.py

## 2026-09-06 — first run from PyCharm

**Step** — Run `05_the_docstring_is_the_interface.py`.

**Command**

```
D:\rtc\trainings\training_agentic_ai_2026_batch_demo\.venv\Scripts\python.exe D:\rtc\trainings\training_agentic_ai_2026_batch_demo\use_case_01\concepts\05_the_docstring_is_the_interface.py
```

**Output**

```
05_the_docstring_is_the_interface.py:39: UserWarning: [EXPERIMENTAL] feature FeatureName.JSON_SCHEMA_FOR_FUNC_DECL is enabled.
  declaration = FunctionTool(make_search_tool(doc))._get_declaration()   # what is sent to Gemini

=== GOOD docstring -> declaration, 590 chars of description
  name        : search_knowledge_base
  parameters  : {'properties': {'question': {'title': 'Question', 'type': 'string'}}, 'required': ['question'], 'title': 'search_knowledge_baseParams', 'type': 'object'}
  description : Search this team's own Northwind Assurance documents.

Use this for any question about policy wordings, cover, exclusions, claims handling,
underwriting appetite, broker terms, complaints procedure, error codes, timescales or
authority limits. Search first; never answer such a question from memory.

Args:
    question: The user's question, in their own words. Do not paraphrase it into keywords.

Returns:
    A dict with a "passages" list; each passage has "source_file" and "clause" (cite both
    as [source_file §clause]), "heading" and "content". An empty list means nothing matched.

=== VAGUE docstring -> declaration, 69 chars of description
  name        : search_knowledge_base
  parameters  : {'properties': {'question': {'title': 'Question', 'type': 'string'}}, 'required': ['question'], 'title': 'search_knowledge_baseParams', 'type': 'object'}
  description : Looks things up.

Args:
    question: a string.

Returns:
    A dict.

Process finished with exit code 0
```

**Analysis**

The point landed. Two identical function bodies produced two declarations that
differ in exactly one field.

Everything mechanical is identical between the runs. Same `name`
(`search_knowledge_base`, taken from `__name__`), and byte-for-byte the same
`parameters` schema — one required string `question` — because ADK derives the
schema from the type annotations, which never changed. The bodies are identical
too: both return `{"passages": []}`.

The only difference is `description`, and it comes wholly from `__doc__`:
590 characters against 69. That is the whole lesson. The docstring is not
documentation for a human reader here; it is the payload sent to Gemini, and it
is the only thing the model has to decide whether to call this tool at all. The
GOOD text names the subject areas, orders the model to search before answering,
tells it not to paraphrase the question, and describes the return shape including
the citation format. The VAGUE text — "Looks things up." — gives the model no
reason to prefer the tool over its own memory, and no idea what to do with the
result.

Note that the docstring is swapped on a *fresh* function object each time
(`make_search_tool`). ADK caches the derived declaration per function object, so
mutating `__doc__` on one reused function would have shown the first declaration
twice and quietly proved nothing.

The `UserWarning` about `FeatureName.JSON_SCHEMA_FOR_FUNC_DECL` being
EXPERIMENTAL is expected and harmless. It is ADK 2.6.3 announcing that it emits
`parameters_json_schema` (plain JSON Schema) rather than the older
`parameters` (`types.Schema`) form. It is printed to stderr, changes nothing
about the run, and the exit code is 0.

`_get_declaration()` is a private method. It is called here deliberately, because
the object it returns is precisely what goes on the wire. Nothing in the demo
depends on it.

**Decides next** — nothing to fix. This script only inspects; it makes no model
call, which is why it needs no credentials and costs nothing. The live
consequence of the vague description — the model answering from memory instead of
searching — is what `TOOL_DESCRIPTION=good|vague` in `demo/.env` switches for the
real agent run.
