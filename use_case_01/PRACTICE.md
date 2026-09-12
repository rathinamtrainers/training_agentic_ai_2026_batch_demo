# PRACTICE — run the eighteen concept programs

This is a run guide. Follow it top to bottom and you will run all eighteen programs.

Each program is small. Run it, read the output, then read its run log
(`use_case_01\concepts\<concept>_RUN_LOG.md`) for the explanation.

Budget about 2 hours.

---

# Part 0 — Setup

Do this once. About five minutes plus a browser login.

### Step 1 — Open PowerShell at the repo root

```
cd D:\rtc\trainings\training_agentic_ai_2026_batch_demo
```

### Step 2 — Create the environment file

```
Copy-Item use_case_01\demo\.env.example use_case_01\demo\.env
```

Open `use_case_01\demo\.env` in an editor and set four values:

| variable | value |
|---|---|
| `GENAI_BACKEND` | `vertex` |
| `GOOGLE_CLOUD_PROJECT` | your GCP project id |
| `GOOGLE_CLOUD_LOCATION` | `global` — **not** `us-central1` |
| `POSTGRES_PASSWORD` | anything you like; the database is local and disposable |

`global` is required. The models used here are only served from the global endpoint.

### Step 3 — Install the packages

```
uv sync --project use_case_01\demo
```

This creates `use_case_01\demo\.venv` with the exact versions the project pins. Takes a second.

### Step 4 — Sign in to Google Cloud

```
gcloud auth application-default login
```

There is no API key to paste. Everything uses this login.

### Step 5 — Start the database

Only concepts 11, 12 and 14 need it, but start it now and forget about it.

```
docker compose --project-directory use_case_01\demo up -d
```

Check it is healthy:

```
docker ps --filter name=sagedesk_uc1_postgres
```

Wait until the status says `Up ... (healthy)`.

### Step 6 — Turn on UTF-8 for this window

```
$env:PYTHONUTF8=1
```

Do this in every new PowerShell window, or the `§` character crashes the scripts.

### Step 7 — Prove the setup works

```
uv run --project use_case_01\demo python use_case_01\concepts\01_tokens_and_the_meter.py
```

If you see two answers and two token counts, setup is done.

---

## Two rules for every command

**Rule 1 — always use the `uv run --project use_case_01\demo` prefix.**
A bare `python script.py` will run, print plausible output, and be wrong, because it
uses whatever packages your global Python has instead of the pinned ones.

**Rule 2 — if you get a `403` naming a project you never configured,**
a shell variable is overriding your `.env`. See it:

```
Get-ChildItem Env: | Where-Object { $_.Name -like "GOOGLE*" }
```

Clear it for this window:

```
Remove-Item Env:GOOGLE_CLOUD_PROJECT
```

---

# Part 1 — Run the programs

Run them in order. After each one, open the matching `_RUN_LOG.md` file to see the
recorded output and the explanation.

Every command below is run from the repo root, `training_agentic_ai_2026_batch_demo`.

## Agent mechanics

### 01 — Tokens and the meter
```
uv run --project use_case_01\demo python use_case_01\concepts\01_tokens_and_the_meter.py
```
Look for: prompt tokens 85 → 160 for the same question, and the thinking tokens you
were billed for but never saw.

### 02 — Non-determinism
```
uv run --project use_case_01\demo python use_case_01\concepts\02_non_determinism.py
```
Look for: how many distinct answers came back at `temperature=0.0`. It is not 1.

### 03 — Structured output
```
uv run --project use_case_01\demo python use_case_01\concepts\03_structured_output.py
```
Look for: the regex quietly dropped passage 1. Nothing crashed.

### 04 — The function-call round trip
```
uv run --project use_case_01\demo python use_case_01\concepts\04_function_call_round_trip.py
```
Look for: three lines — model asks for the tool, **your code** runs it, model answers.

### 05 — The docstring is the interface
```
uv run --project use_case_01\demo python use_case_01\concepts\05_the_docstring_is_the_interface.py
```
Look for: 590 characters of description versus 69, from the same function.
The `[EXPERIMENTAL] JSON_SCHEMA_FOR_FUNC_DECL` warning is expected — ignore it.

### 06 — The ADK agent and its event stream
```
uv run --project use_case_01\demo python use_case_01\concepts\06_adk_agent_and_its_event_stream.py
```
Look for: prompt tokens 108 → 236. The whole history is resent every turn.

### 07 — The cap and the budget
```
uv run --project use_case_01\demo python use_case_01\concepts\07_the_cap_and_the_budget.py
```
Look for: the queries getting worse each time, and the cost increments growing.

## Environment

### 08 — Pins move together
```
uv run --project use_case_01\demo python use_case_01\concepts\08_pins_move_together.py
```
Look for: the two version pins that cannot move independently.

## Retrieval

### 09 — A chunk is a clause
```
uv run --project use_case_01\demo python use_case_01\concepts\09_a_chunk_is_a_clause.py
```
Look for: the citation `[wording.md §3+4]` — one chunk holding both a "no" and a "yes".

### 10 — Embeddings and the task type
```
uv run --project use_case_01\demo python use_case_01\concepts\10_embeddings_and_the_task_type.py
```
Look for: the irrelevant passage scoring 0.485, not 0.

### 11 — pgvector is the store  *(database needed)*
```
uv run --project use_case_01\demo python use_case_01\concepts\11_pgvector_is_the_store.py
```
Look for: the same scores as concept 10, from plain Postgres.

### 12 — Hybrid search and RRF  *(database needed)*
```
uv run --project use_case_01\demo python use_case_01\concepts\12_hybrid_search_and_rrf.py
```
Look for: the keyword search returning empty even for a row containing the exact code.

### 13 — The reranker and the floor
```
uv run --project use_case_01\demo python use_case_01\concepts\13_the_reranker_and_the_floor.py
```
Look for: the second question where all four passages score 0.00 and nothing survives.

## Boundaries and proof

### 14 — The tenant filter lives in the query  *(database needed)*
```
uv run --project use_case_01\demo python use_case_01\concepts\14_the_tenant_filter_lives_in_the_query.py
```
Look for: `cross-tenant rows in that result: 2 -- no error, no log line.`

### 15 — No argument in which to ask
```
uv run --project use_case_01\demo python use_case_01\concepts\15_no_argument_in_which_to_ask.py
```
Look for: agent 2 saying it cannot access the Claims documents, after reading them.

### 16 — A citation you can open
```
uv run --project use_case_01\demo python use_case_01\concepts\16_a_citation_you_can_open.py
```
Look for: run 3 — fluent, confident, wrong, and quoting dollars at a UK insurer.

### 17 — The golden set
```
uv run --project use_case_01\demo python use_case_01\concepts\17_the_golden_set.py
```
Look for: precision 0.33 without the reranker, 0.83 with it.

### 18 — Streaming and the late verdict
```
uv run --project use_case_01\demo python use_case_01\concepts\18_streaming_and_the_late_verdict.py
```
Look for: the ungrounded answer on screen at 9.84s, the verdict arriving at 11.08s.

---

# Part 2 — Tidy up

Stop the database when you are done:

```
docker compose --project-directory use_case_01\demo down
```

Add `-v` to that command if you also want to delete the stored data.

---

# If something breaks

| symptom | cause | fix |
|---|---|---|
| `No API key was provided` | no `use_case_01\demo\.env` file | Part 0, step 2 |
| `403 PERMISSION_DENIED`, unfamiliar project | shell variable beating `.env` | `Remove-Item Env:GOOGLE_CLOUD_PROJECT` |
| `404 NOT_FOUND` on the model | `GOOGLE_CLOUD_LOCATION=us-central1` | set it to `global` |
| `PackageNotFoundError` / odd versions | you used a bare `python` | add `uv run --project use_case_01\demo` |
| `connection refused` on port 5432 | database not started | Part 0, step 5 |
| `UnicodeEncodeError` on `§` | console encoding | `$env:PYTHONUTF8=1` |
| `[EXPERIMENTAL] JSON_SCHEMA_FOR_FUNC_DECL` | nothing is wrong | ignore it |
