# 04 — The function call round trip

`../04_function_call_round_trip.py`

## Summary

The script proves one claim: **the model does not run your code.** It asks.

It sends a single question — *"is escape of water from a neighbouring flat
covered?"* — to Gemini, having first told the model that a function called
`search_knowledge_base` exists. The model does not answer. It replies with a
`function_call` part: the name of the function it wants and the arguments it
chose. The script then runs that function itself, as ordinary Python, in its own
process, and appends the return value to the conversation as a
`function_response`. Only then does the model produce prose.

The whole exchange is printed as three lines, and those three lines are the
lesson:

```
MODEL REQUESTS TOOL > search_knowledge_base({'question': '...'})
RUNTIME RETURNS     > {'passages': [...]}
MODEL ANSWERS       > Yes, escape of water ... subject to an excess of £350.
```

Four messages travel the wire in total: user text → model `function_call` →
our `function_response` → model text. Everything else in the file is scaffolding
around that shape.

The script is deliberately raw. It uses `google-genai` directly, with automatic
function calling switched **off**, so that every step of the round trip is
visible in the code rather than hidden inside a framework. Script 06 shows the
same idea again with ADK doing the loop for you; this one shows what ADK is
doing.

---

## Aspect by aspect

### 1. Configuration, resolved from the script's own location

```python
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
```

The `.env` is found relative to `__file__`, not the working directory. That is
why the script runs correctly from PyCharm, from `concepts/`, or from anywhere
else — there is no working-directory dependency to get wrong. The one `.env`
under `demo/` serves the whole use case, so the concept scripts and the demo
never drift apart on model ids or credentials.

```python
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()
```

`genai.Client()` takes no arguments. That is the point of these two lines: the
SDK reads its entire configuration from the environment —
`GOOGLE_GENAI_USE_VERTEXAI` to choose the backend, then either `GOOGLE_API_KEY`
or the pair `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` plus Application
Default Credentials. Swapping a free API key for a Google Cloud project changes
no line of code, only `GENAI_BACKEND` in the `.env`.

`setdefault` rather than assignment: an environment variable already exported in
the shell wins over the `.env`. That is the usual precedence and it makes a
one-off override easy.

On the Vertex path `GOOGLE_CLOUD_LOCATION` must be `global` for the `gemini-3.x`
models. A regional value returns `404 NOT_FOUND` for `gemini-3.7-flash`. The
default written in the code is only a fallback; the pinned value lives in the
`.env`.

### 2. The corpus — deliberately trivial

```python
CORPUS = [("01_escape_of_water.md", "4", "Escape of water from a neighbouring flat is covered. Excess GBP 350."),
          ("11_broker_commission.md", "6", "Broker commission is settled monthly in arrears.")]
```

Two tuples of *(file, clause, text)*. No database, no embeddings, no vector
store. Retrieval quality is not what this script teaches, and a real retriever
here would only add moving parts that can fail during a live demonstration. The
shape of each record — a source file and a clause number alongside the text — is
the shape a citation needs, which is why it is carried even in the toy version.
Script 16 picks that thread up.

Note that the second entry exists purely to be *not* returned. Without a
distractor, the search proves nothing.

### 3. The tool — ordinary Python, in our process

```python
def search_knowledge_base(question: str) -> dict:
    words = set(question.lower().split())
    return {"passages": [{"source_file": f, "clause": c, "content": t} for f, c, t in CORPUS
                         if words & set(t.lower().split())][:1]}
```

A plain function. It takes a string, does a crude word-overlap match, and returns
a dict. There is nothing AI about it, and nothing special registers it with the
model.

`words & set(...)` is set intersection: keep a passage if the question and the
passage share at least one word. It is naive on purpose — a stand-in for the
hybrid search that `demo/retrieval.py` does properly. `[:1]` caps the result at a
single passage so the printed output stays readable on a slide.

The return type is a `dict` because the value has to survive being serialised
into JSON and sent back over the wire. A dict of primitives does; a custom object
would not.

### 4. The declaration — what the model is actually given

```python
TOOL = types.Tool(function_declarations=[types.FunctionDeclaration(
    name="search_knowledge_base",
    description="Search this Northwind team's own documents. Search before answering; never answer from memory.",
    parameters=types.Schema(type=types.Type.OBJECT, required=["question"], properties={
        "question": types.Schema(type=types.Type.STRING, description="the user's question, in their own words")}))])
```

This is the single most important thing to understand about tool use: **the model
never sees the function.** It sees this declaration — a name, a description, and
a JSON-Schema-shaped parameter spec. Nothing more. The body of
`search_knowledge_base` could be deleted and the model would still ask for it in
exactly the same way.

So the declaration is the interface, and every word in it is load-bearing:

- **`name`** must match the Python function the script will dispatch to. Here the
  match is made by hand, in `search_knowledge_base(**args)`.
- **`description`** is the instruction the model obeys. *"Search before
  answering; never answer from memory"* is what stops the model answering an
  insurance question out of its training data. Weaken this sentence and the model
  stops calling the tool — which is precisely the experiment script 05 runs, and
  why the `.env` carries a `TOOL_DESCRIPTION=good|vague` switch.
- **`parameters`** declares one required string, `question`. Its own description
  — *"the user's question, in their own words"* — tells the model to pass the
  question through rather than paraphrase it into keywords.

`required=["question"]` matters: without it the model may call the function with
no arguments at all, and `search_knowledge_base(**{})` would raise a `TypeError`.

### 5. The history is the state — there is no session

```python
history = [types.Content(role="user", parts=[types.Part(text="is escape of water ...?")])]
```

Gemini is stateless. `history` is a plain Python list, and it *is* the
conversation. Every turn resends the whole list. Nothing is remembered on the
server; if the list is not appended to, the model has no idea a tool was ever
called.

Each element is a `Content` with a `role` and a list of `parts`. A part carries
exactly one of: text, a `function_call`, or a `function_response`. That is the
whole vocabulary of the wire format.

### 6. Automatic function calling, switched off

```python
config = types.GenerateContentConfig(tools=[TOOL], automatic_function_calling={"disable": True})
```

Left on its default, the SDK would notice the `function_call`, look up a Python
callable, invoke it, append the response and call the model again — all inside
one `generate_content()`. You would get the final answer and see none of the
middle. Disabling it forces the loop into the open, where it can be read.

This is exactly what ADK does for you in script 06. The difference is visibility,
not capability.

### 7. The loop

```python
while True:
    reply = client.models.generate_content(model=MODEL, contents=history, config=config)
    part = reply.candidates[0].content.parts[-1]
    history.append(reply.candidates[0].content)
    if not part.function_call:
        print(f"MODEL ANSWERS       > {part.text.strip()}")
        break
```

`while True` is honest: the number of tool calls is not known in advance. The
model may search once, search again with a different question, then answer. The
loop exits on content, not on a counter.

`candidates[0]` — one candidate, because no `candidate_count` was requested.

`parts[-1]` — the last part of the reply. A model may emit reasoning text
alongside its call; the call is what the script acts on.

`history.append(reply.candidates[0].content)` appends the model's own turn
**before** anything else happens, and it appends the whole `Content`, not the
part. This is easy to get wrong, and getting it wrong is fatal: a
`function_response` that does not follow its matching `function_call` in the
history is rejected by the API. Request and response must be paired, in order.

```python
    result = search_knowledge_base(**dict(part.function_call.args))   # <-- WE run it, not the model
```

The comment is the title of the script. `part.function_call.args` is a map type
from the protobuf layer, so `dict(...)` makes it a real dict before `**`
unpacking it into the call. The dispatch is a hard-coded call to one known
function — with several tools you would keep a `{name: callable}` registry and
look it up, which is all a framework's tool router really is.

Note what is *not* here: no validation of the arguments, no `try`/`except`. In
production both belong. The model chooses these arguments, and a model's choice
is untrusted input — the same class of thing as a value from an HTTP request.
`demo/guardrails.py` is where that lesson lands.

```python
    history.append(types.Content(role="user", parts=[types.Part.from_function_response(
        name=part.function_call.name, response=result)]))
```

The result goes back as `role="user"` — the tool result arrives from *our* side
of the conversation, not the model's. `from_function_response` wraps the dict in
the right part type, and `name` is what ties the response to the call that asked
for it. The dict must be JSON-serialisable, which is why the tool returns
primitives.

Then the loop turns, the model sees a history that now contains its own request
and our answer, and it writes the prose.

---

## What to take away

- The model emits a *request*. Your runtime performs the *action*. That boundary
  is where every permission check, audit log and tenant filter belongs — the
  model is on the wrong side of it to be trusted with any of them.
- The declaration, not the function, is the interface. The description is the
  instruction the model actually follows.
- The history is the state, it lives in your process, and a call and its response
  must stay paired and in order.
- Tool arguments are model-chosen and therefore untrusted.

## Related

- `05_the_docstring_is_the_interface.py` — weaken the description, watch the
  model stop calling the tool.
- `06_adk_agent_and_its_event_stream.py` — the same round trip, run by ADK, seen
  as events.
- `14_the_tenant_filter_lives_in_the_query.py` — why the filter goes in the code
  that runs the tool, never in the prompt.
- `../run_logs/04_function_call_round_trip_RUN_LOG.md` — recorded runs.
