# Demo 1 — Core building blocks

The first six concepts from [`../adk_concepts.md`](../adk_concepts.md), in one runnable file.

| Concept | Where to look in `core_agent.py` |
|---|---|
| `Agent` | the `tutor = Agent(...)` block |
| `instruction` | the system prompt inside that block |
| `model` | the `MODEL` constant, a Gemini model served by Vertex AI |
| `description` | the outward-facing one-liner, unused until agents delegate |
| `Runner` | `InMemoryRunner` in `main()` |
| `Event` | the `async for event in runner.run_async(...)` loop |

## Before you run it

This demo uses **Vertex AI**, not an API key. Authenticate once:

```
gcloud auth application-default login
```

The project and region are set at the top of the script and default to
`agentic-ai-2026-demo` / `us-central1`. Override them with `VERTEX_PROJECT` and
`VERTEX_LOCATION` to use your own project; that project needs the Vertex AI API
enabled.

The script deliberately does **not** read `.env`. `.env` configures the API-key
path used elsewhere in the course, and mixing the two is the fastest way to a
confusing 403.

## Run it

```
uv run python adk_01_core/core_agent.py
uv run python adk_01_core/core_agent.py "How does an Agent differ from a Tool?"
```

Both default questions share one session, so the second question ("And what is
an Event?") only makes sense because the history lives in the session. That is
the point worth pausing on in class.
