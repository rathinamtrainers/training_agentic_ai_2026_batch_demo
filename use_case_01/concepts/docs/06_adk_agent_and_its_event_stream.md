# 06 — An ADK agent and its event stream

`../06_adk_agent_and_its_event_stream.py`

## Summary

This is script 04 again, with ADK doing the loop.

An `Agent` is three things: a model, an instruction, and a list of tools. A
`Runner` is what drives it — it holds the session, sends the turn, notices the
`function_call`, runs the Python function, appends the `function_response`, and
calls the model again. The `while True` loop written by hand in script 04 is now
someone else's code.

What you get in exchange for that loop is an **event stream**. `run_async` is an
async generator, and it yields an event for every step: the model's tool request,
the tool's result, the final text. The script prints each one as it arrives, so
the same four-message round trip is still visible — just observed rather than
driven.

Running 04 and 06 back to back is the point. Identical wire traffic, two levels
of abstraction.

---

## Aspect by aspect

### 1. Configuration

The standard preamble, with one difference: no `genai.Client()`. ADK constructs
its own client from the same environment variables. `MODEL` is still read from
the `.env`.

### 2. The tool is a plain function with a docstring

```python
def search_knowledge_base(question: str) -> dict:
    """Search this Claims team's own Northwind documents. Args: question: the user's question."""
    return {"passages": [{"source_file": "01_escape_of_water.md", "clause": "4",
                          "content": "Escape of water from a neighbouring flat is covered. Excess GBP 350."}]}
```

No `types.Tool`, no `FunctionDeclaration`, no `Schema`. ADK derives all of it —
name from `__name__`, parameters from the annotations, description from the
docstring. That derivation is script 05, and this is what it buys: the twelve
lines of declaration in script 04 collapse to a docstring.

The function is a stub that ignores its argument and always returns the same
passage. Retrieval is not what is being taught here.

### 3. The agent

```python
agent = Agent(name="grounded_answer_service", model=MODEL, tools=[search_knowledge_base],
              instruction="Answer only from the passages the tool returns, and cite every claim"
                          " inline as [source_file §clause]. Two sentences at most.")
```

Four arguments and that is a complete agent.

- **`name`** identifies the agent, and it is what shows up as `event.author` in
  the stream below. It must be a valid identifier.
- **`model`** is the model id string. The agent is not bound to a client object.
- **`tools`** takes the bare Python function. ADK wraps it in a `FunctionTool`
  itself.
- **`instruction`** becomes the system instruction. Three orders in one sentence:
  ground the answer in the tool output, cite in a fixed format, keep it short.
  The citation format appears here *and* in the tool's `Returns:` description in
  the fuller version — belt and braces, because it is what script 16 checks.
  "Two sentences at most" is a cost control; output tokens are the expensive ones
  (script 01).

Note what the instruction does not do: it does not tell the model *when* to
search. That belongs in the tool description, because it is a fact about the
tool, not about the agent.

### 4. Runner and session

```python
runner, session = InMemoryRunner(agent=agent, app_name="concepts"), uuid.uuid4().hex[:8]
await runner.session_service.create_session(app_name="concepts", user_id="claims", session_id=session)
```

`InMemoryRunner` is the laptop runner: sessions live in a dict and vanish when
the process exits. The production alternatives (a database-backed session
service, or Agent Runtime's own) swap in at this line and nowhere else.

The three-part key — `app_name`, `user_id`, `session_id` — is the same everywhere
in ADK. `user_id="claims"` is a stand-in for identity; in the real service that
value comes from the `X-Northwind-Team` header. The session must be created
before it is used; `run_async` will not conjure one.

The random `session_id` gives every run a clean history. Reuse the id and the
previous turn is still there, which is a fine way to demonstrate memory and a
confusing way to demonstrate anything else.

### 5. The event loop

```python
async for event in runner.run_async(user_id="claims", session_id=session, new_message=question):
```

This is the abstraction ADK offers in place of script 04's `while True`. It is
an async generator, so events arrive as they happen rather than in a list at the
end — which is what makes streaming possible (script 18).

```python
        for part in (event.content.parts if event.content and event.content.parts else []):
```

An event does not always carry content — some are usage-only or
control-only — so the guard is necessary, not defensive noise. And a single
event's content may hold several parts.

```python
            if part.function_call:
                print(f"  [{event.author}] function_call     ...")
            elif part.function_response:
                print(f"  [{event.author}] function_response {part.function_response.response}")
            elif part.text and part.text.strip():
                print(f"  [{event.author}] text (final={event.is_final_response()}) ...")
```

The same three part types as script 04 — `function_call`, `function_response`,
text — because it is the same wire format. Nothing about ADK changes what Gemini
speaks.

`event.author` is worth watching. The tool request and the final text are
authored by the agent's name; the tool result is authored by the tool. In a
multi-agent setup this is how you tell which agent produced what.

`event.is_final_response()` distinguishes the answer from intermediate text. An
agent may emit text mid-turn; only the final event is the one to show a user, and
only the final event is the one a guardrail can judge — which is exactly the
problem script 18 runs into.

### 6. Usage, per event

```python
        if event.usage_metadata:
            print(f"      usage: prompt {event.usage_metadata.prompt_token_count} tokens")
```

Usage arrives per model call, not per turn. A turn with one tool call makes two
model calls and therefore reports twice, and the second prompt count is larger
than the first — because the first prompt plus the tool request plus the tool
result is what the second call sends. Watching that number grow is script 01's
lesson appearing on its own: **a tool-using turn re-sends the whole history every
time.** That is the real cost of a multi-step agent, and it is why script 07 caps
the number of steps.

### 7. Shutdown

```python
    await runner.close()
```

Releases the runner's resources. `asyncio.run(main())` at module level is the
whole entry point — everything in ADK's runner API is async.

---

## What to take away

- An agent is a model, an instruction and a tool belt. The runner is the loop.
- ADK writes the declaration from your function; you write the docstring.
- The event stream is the observability. Every tool call, tool result and text
  part is visible — do not treat the agent as a black box that returns a string.
- Usage is reported per model call. A turn with N tool calls costs N+1 calls, each
  sending a longer history than the last.
- The instruction governs the agent; the tool description governs the tool. Keep
  each fact where it belongs.

## Related

- `04_function_call_round_trip.py` — the same round trip, driven by hand.
- `05_the_docstring_is_the_interface.py` — where the declaration comes from.
- `07_the_cap_and_the_budget.py` — what happens when the loop does not end.
- `18_streaming_and_the_late_verdict.py` — the event stream taken to the client.
- `demo/agent.py`, `demo/turn.py` — the shipping agent and its runner.
- `../run_logs/06_adk_agent_and_its_event_stream_RUN_LOG.md` — recorded runs.
