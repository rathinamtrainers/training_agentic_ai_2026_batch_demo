# docs

Written explanations of the numbered concept scripts in `use_case_01/concepts/`.

One document per script, named after it: `04_function_call_round_trip.py` is
explained in `04_function_call_round_trip.md`. Each opens with a summary of what
the script does and why it exists, then walks the code aspect by aspect, and ends
with what to take away and where the idea is picked up again.

These are teaching notes, not API reference. They explain why the code is shaped
the way it is and which line carries the lesson. For the record of actual runs —
command, output, analysis — see `../run_logs/`.

The `.env` preamble shared by nearly every script is explained once, in
`04_function_call_round_trip.md`, and referred to from the others rather than
repeated.

## The scripts, in order

**The model** — what you are calling, and what it costs.

| | |
| --- | --- |
| [01](01_tokens_and_the_meter.md) | Tokens are the window and the invoice, and retrieval writes most of the bill. |
| [02](02_non_determinism.md) | The same question twice is two answers, and temperature 0 is not a promise. |
| [03](03_structured_output.md) | Ask for data, not prose: a response schema is enforced, a regex is hope. |

**Tools and agents** — how the model reaches your code.

| | |
| --- | --- |
| [04](04_function_call_round_trip.md) | The model does not run your code. It asks, and your runtime answers. |
| [05](05_the_docstring_is_the_interface.md) | The model never sees your function, only the declaration ADK builds from your docstring. |
| [06](06_adk_agent_and_its_event_stream.md) | An agent is a model, an instruction and a tool belt; a runner streams the events. |
| [07](07_the_cap_and_the_budget.md) | The agent decides when it is finished, so your loop decides when it may not continue. |
| [08](08_pins_move_together.md) | A pin is a constraint other packages have opinions about. |

**Retrieval** — getting the right passage into the window.

| | |
| --- | --- |
| [09](09_a_chunk_is_a_clause.md) | Cut on the clause boundary, because a clause is what a citation points at. |
| [10](10_embeddings_and_the_task_type.md) | Text in, 768 numbers out — and similarity is arithmetic, not magic. |
| [11](11_pgvector_is_the_store.md) | The vectors live in Postgres and the search is one SQL statement. |
| [12](12_hybrid_search_and_rrf.md) | Run both searches and fuse them by rank; their scores do not compare. |
| [13](13_the_reranker_and_the_floor.md) | A second, more expensive opinion — and the floor is what lets the service refuse. |

**Boundaries** — who may read what, and what may reach the user.

| | |
| --- | --- |
| [14](14_the_tenant_filter_lives_in_the_query.md) | The tenant boundary belongs inside the SQL, where nobody can forget to call it. |
| [15](15_no_argument_in_which_to_ask.md) | Bind the tenant when the tool is built. A missing parameter is a fact. |
| [16](16_a_citation_you_can_open.md) | Parse every citation on the way out, and open it. |
| [17](17_the_golden_set.md) | A labelled set turns "it feels better" into a number that can move. |
| [18](18_streaming_and_the_late_verdict.md) | Streaming buys latency and costs certainty. |

## Running them

Scripts 11, 12 and 14 need the database:

```
docker compose -f ../demo/docker-compose.yml up -d
```

Scripts 05 and 08 make no model call and need no credentials — 08 does reach PyPI
over HTTP. Everything else calls Gemini using the credentials in
`../demo/.env`.
