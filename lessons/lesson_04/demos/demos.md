# Lesson 4 — The same loop inside a framework: demonstrations

Four demos. All four run one file, `adk_invoice_agent.py`. It is the lesson 1 invoice agent,
rebuilt in **Google ADK**. It talks to the same local model as lessons 1 to 3.

Objective 1.5, word for word: *Rebuild the same loop in a framework, and point to where each
hand-written part now lives.*

| # | Demo | Serves | Lands after |
|---|---|---|---|
| 1 | The same agent, twice: hand-written, then ADK | 1.5, "rebuild" and "point to" | Slide 3. Refer back to it through slide 9 |
| 2 | Set the call cap to one | 1.5, the step cap | Slide 10, "A cap you did not choose" |
| 3 | The budget, moved into a callback | 1.5, the token budget | Slide 11, "The budget stays yours" |
| 4 | One file, two ADK versions | 1.5, and the lesson's recorded trap | Slide 14, "Pin it, and move when you choose" |

Every output quoted below was seen on this machine on 2026-10-15. The full, unedited output
of every command is in `adk_invoice_agent_RUN_LOG.md`.

**Why ADK.** It is the first framework this course deploys (lesson 11). The speech's examples
(the runner, the session service, `max_llm_calls`, the `${var}` change) are ADK's. Lesson 3's
`tool_lab.py` also says "Lesson 4 shows a framework doing the same thing."

Slides 12 and 13 get no demo. Slide 12 (the model still varies) was shown in lesson 1, demo 4.
Slide 13 (old names) is a reading point, not a thing that runs.

## Before the session (once, about ten minutes)

1. Ollama running, with the lesson 1 model pulled. Do this the day before:

   ```
   ollama pull qwen3:4b-instruct
   ```

2. Open a terminal in this folder. Make the main environment:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   On macOS or Linux the second line is `source .venv/bin/activate`.

3. Make the second environment. Only demo 4 needs it:

   ```
   python -m venv .venv-adk28
   .venv-adk28\Scripts\pip install -r requirements-adk28.txt
   ```

4. Warm the model up ten minutes before class:

   ```
   ollama run qwen3:4b-instruct "hello"
   ```

5. Open `adk_invoice_agent.py` in an editor beside the terminal. Open
   `../../lesson_01/demos/invoice_agent.py` in a second tab. Demo 1 points at both.

6. Make the terminal font large.

**The files in this folder:**

- `adk_invoice_agent.py` — the program. Four modes, one per demo.
- `invoices.csv` — the same twelve invoices as lesson 1. Invoice 4471 is paid on 2026-03-12.
- `requirements.txt` — `google-adk==2.10.0`, `google-genai==2.31.0`, `litellm==1.105.1`.
  Pinned exactly, because pinning is what this lesson teaches.
- `requirements-adk28.txt` — the same, with `google-adk==2.8.0`. For demo 4.
- `adk_invoice_agent_RUN_LOG.md` — what every command printed.

**Which ADK, and why.** 2.10.0 is the version the 2026-10-01 research recommends. PyPI's
newest on 2026-10-15 is 2.12.0, and that version was not run. Do not let the room's
`pip install google-adk` with no version persuade you it is the same thing.

**How ADK reaches Ollama.** Through LiteLLM, with the model string
`ollama_chat/qwen3:4b-instruct`. ADK's own Ollama page says use `ollama_chat`, not `ollama`.
Its reason is that `ollama` "can result in unexpected behaviors such as infinite tool call
loops." The base URL comes from `OLLAMA_API_BASE`. The program sets it to
`http://127.0.0.1:11434` if it is unset.

**Timing.** On the test machine (CPU only, shared) one demo took 20 seconds to three minutes.
Demo 3 and demo 4 were the slow ones, at up to three minutes each. Run every demo once on the
class laptop the day before and note the times.

**Your run may differ.** The model is not deterministic (lesson 1). In these runs the tool
call and the facts were the same every time. The sentences changed a little. Demo 4's model
answer changed between runs; the instruction it was given did not.

**If Ollama is down**, LiteLLM raises a connection error with a long traceback. Start Ollama
and run the command again.

---

## Demo 1 — The same agent, twice: hand-written, then ADK

**What it shows.** The same question, the same tool, the same model, run through lesson 1's
forty-line loop and then through ADK. Same path, same facts, about the same tokens. Then the
trainer points at the line in the ADK file where each hand-written piece went. (Objective
1.5, both halves.)

**When in the lesson.** Run it at slide 3, after "Have a guess, and notice that you cannot see
it anywhere in those six lines." Leave the output on screen. Point back at it on slides 4, 6,
7, 8 and 9. Each of those slides is one line in the output.

**Setup.** Main environment active. Ollama warm.

**What the trainer does.**

1. Run the hand-written loop from lesson 1 first:

   ```
   python ..\..\lesson_01\demos\invoice_agent.py trace
   ```

2. Run the ADK version:

   ```
   python adk_invoice_agent.py trace
   ```

3. Put the two outputs side by side. Read the two token lines and the two answers.
4. Open `adk_invoice_agent.py` at `cmd_trace` and `run`. Point at the four marked lines:
   - `Runner(...)` in `run`, marked `THE LOOP lives in here`. (Slide 3.)
   - `InMemorySessionService()`, marked `THE MESSAGES LIST lives in here`. (Slide 4.)
   - `tools=[lookup_invoice]`, marked `THE TOOL REGISTRY: a list`. (Slide 6.)
   - `LiteLlm(model=f"ollama_chat/{MODEL_NAME}")`, marked `THE MODEL CLIENT: one string`. (Slide 8.)
5. Scroll up to the JSON block, "what ADK built from our function". Read the `description`
   aloud. (Slide 7.)
6. Scroll down to "the session after the run". (Slide 4.)

**What the room sees.**

The hand-written loop:

```
=== step 1: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 2 messages, roles ['system', 'user']
  cost        : input 214 tokens, output 24 tokens   (run total so far: 238)
  model asked : lookup_invoice({"invoice_number":4471})   <- the model decided; nothing has run yet
...
=== step 2: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 4 messages, roles ['system', 'user', 'assistant', 'tool']
  cost        : input 317 tokens, output 44 tokens   (run total so far: 599)
...
>>> outcome: ANSWERED   steps: 2   tokens this run: 599
```

The ADK version, same question:

```
google-adk 2.10.0 | model ollama_chat/qwen3:4b-instruct at http://127.0.0.1:11434
session created: id 5aadd9f3-a25c-415e-968c-ed866c6f8070 for user 'priya', events in it: 0

=== what ADK built from our function, sent with every model call ===
{
  "description": "Look up one invoice in the finance database by its number.\n\nReturns customer, amount, status (paid/unpaid), paid_on date and payment reference.\n\nArgs:\n    invoice_number: The invoice number, e.g. 4471",
  "name": "lookup_invoice",
  "parameters_json_schema": {
    "properties": {
      "invoice_number": {
        "title": "Invoice Number",
        "type": "integer"
      }
    },
    "required": [
      "invoice_number"
    ],
    "title": "lookup_invoiceParams",
    "type": "object"
  }
}

=== model call 1 (event by 'invoice_agent') ===
  cost        : input 234 tokens, output 24 tokens   (run total so far: 258)
  model asked : lookup_invoice({"invoice_number": 4471})
  --- ADK calls our function lookup_invoice(4471) ---
  credentials : OS user 'rtc', pid 5140 - this process's rights
  tool result : {"invoice_number": "4471", "customer": "Calder Engineering", "amount_eur": "2380.00", "status": "paid", "paid_on": "2026-03-12", "payment_reference": "PAY-88177"}   <- ADK appended this to the session

=== model call 2 (event by 'invoice_agent') ===
  cost        : input 337 tokens, output 56 tokens   (run total so far: 651)
  model said  : 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering for an amount of €2380.00. The payment reference is PAY-88177.'   <- no tool request: ADK stops the loop

>>> model calls: 2   tokens this run: 651   46.1 s

=== the session after the run: 4 events (this was your messages list) ===
  1. author=user           ['text']
  2. author=invoice_agent  ['function_call']
  3. author=invoice_agent  ['function_response']
  4. author=invoice_agent  ['text']
```

**What it proves.**

- **Same loop.** Two model calls in both. One tool call, same argument, same facts. The loop
  is still there; it moved into `Runner`. (Slide 3.)
- **The list became a session.** Lesson 1 sent `['system', 'user', 'assistant', 'tool']`.
  ADK's session holds the same four things as events: user text, function call, function
  response, answer. The system prompt is not an event; ADK adds it to every request.
  (Slide 4.)
- **The tool runs in our process.** The `credentials` line is printed from inside our
  function. ADK called it; the rights are still this OS user's. (Lesson 1, objective 1.1.)
- **The registry was built from our words.** Name, type hint and docstring became the JSON
  above. (Slide 6.)
- **Read what it built.** This is the slide 7 point, and the JSON shows it live. Lesson 3
  said each `Args:` line becomes a parameter description. Here, in ADK 2.10.0, it did not.
  The whole docstring, `Args:` block and all, went into the tool's `description`. The
  parameter got only a `title`. The framework did the plumbing. What it did with your words
  is something you check, not something you assume.
- **About 30 more input tokens per call** (234 against 214, 337 against 317). ADK adds a line
  to the system prompt. Demo 4 shows the line: `You are an agent. Your internal name is
  "tenant_agent".` The framework is not free in tokens either.
- **The stop rule is gone from our code.** "No tool request: ADK stops the loop." There is no
  `if not reply.get("tool_calls")` in `adk_invoice_agent.py`. (Slide 9.)

**The trap the room brings.** Someone will expect the framework version to give a different,
"smarter" answer. It gives the same answer, because it is the same model. The framework adds
no intelligence. That is slide 2's sentence, shown.

---

## Demo 2 — Set the call cap to one

**What it shows.** The step cap still exists, as a setting called `max_llm_calls`. Its
default is 500. Set it to one and watch the real failure. (Objective 1.5, the step cap.)

**When in the lesson.** At the end of slide 10, after "It is a bigger bill with a ceiling on
it." The speech's lab (slide 16) asks learners to do exactly this, so this is them seeing it
first.

**Setup.** Main environment active. Ollama warm.

**What the trainer does.**

1. Run with the cap set in code:

   ```
   python adk_invoice_agent.py cap --max-llm-calls 1
   ```

2. Let the traceback scroll. Do not clear it. Scroll to the bottom.
3. Point at the first line of the output: the default is 500.
4. Run it again with the cap set by environment variable, no code change.
   In PowerShell:

   ```
   $env:ADK_MAX_LLM_CALLS = "1"
   python adk_invoice_agent.py cap
   Remove-Item Env:ADK_MAX_LLM_CALLS
   ```

   In `cmd.exe`, use `set ADK_MAX_LLM_CALLS=1`, then `set ADK_MAX_LLM_CALLS=` to clear it.

**What the room sees.** The first line, then one model call, then the tool runs:

```
google-adk 2.10.0 | model ollama_chat/qwen3:4b-instruct at http://127.0.0.1:11434 | RunConfig().max_llm_calls default here: 500 (ADK_MAX_LLM_CALLS=None) | this run: 1

=== model call 1 (event by 'invoice_agent') ===
  cost        : input 234 tokens, output 24 tokens   (run total so far: 258)
  model asked : lookup_invoice({"invoice_number": 4471})
  --- ADK calls our function lookup_invoice(4471) ---
```

Then ADK logs two full tracebacks, 168 lines between them, at ERROR level. They are ADK's own log
lines, not the program's. The first one ends:

```
google.adk.agents.invocation_context.LlmCallsLimitExceededError: Max number of llm calls limit of `1` exceeded
```

Then the program catches the exception and prints the session:

```
>>> google.adk.agents.invocation_context.LlmCallsLimitExceededError: Max number of llm calls limit of `1` exceeded
>>> the session kept 4 events:
  1. author=user           ['text']
  2. author=invoice_agent  ['function_call']
  3. author=invoice_agent  ['function_response']
  4. author=invoice_agent  []  error_code='LlmCallsLimitExceededError' error_message='Max number of llm calls limit of `1` exceeded'
```

The environment-variable run prints the same, with a different first line:

```
... | RunConfig().max_llm_calls default here: 1 (ADK_MAX_LLM_CALLS='1') | this run: 1
```

**What it proves.**

- **The cap moved; it did not vanish.** Lesson 1's `for step in range(1, max_steps + 1)` is
  now `RunConfig(max_llm_calls=...)`, or `ADK_MAX_LLM_CALLS` in a deployment.
- **The default is 500.** Two calls answered this question. An agent you never configured
  may make 500 model calls before anything stops it. That is the "limit you did not choose".
- **Read where it fired.** The cap counts model calls, not loop steps. Call 1 ran. The tool
  ran. Call 2 was refused before it was sent. The tool's work is in the session; the answer
  is not.
- **The failure at two in the morning** is a wall of traceback. The one line that matters is
  at the bottom of the first block. ADK also writes it into the session as an error event.
  So a session store you can query will tell you why a run stopped.

**The trap the room brings.** Most expect the cap to stop the agent with a polite message.
It raises an exception. Code that does not catch `LlmCallsLimitExceededError` crashes the
request.

---

## Demo 3 — The budget, moved into a callback

**What it shows.** No framework refuses a model call for cost. ADK gives a hook that runs
before each model call. Lesson 1's budget check goes into that hook, and refuses the call
that would have cost 827,000 tokens. (Objective 1.5, the token budget.)

**When in the lesson.** At slide 11, after "You build that yourself, with a callback that runs
before each model call, and you decide what to do when it trips." Then say slide 11's last
paragraph over the output.

**Setup.** Main environment active. Ollama warm. Have lesson 1's `invoice_agent.py` open at
the line marked `# LIMIT 3: budget, checked BEFORE`.

**What the trainer does.**

1. Show `make_budget_guard` in `adk_invoice_agent.py`. It is lesson 1's `LIMIT 3` with a new
   home: `before_model` checks, `after_model` adds up what was spent.
2. Show where it is plugged in: `before_model_callback=before, after_model_callback=after`
   in `cmd_budget`.
3. Run it:

   ```
   python adk_invoice_agent.py budget
   ```

**What the room sees.**

```
google-adk 2.10.0 | model ollama_chat/qwen3:4b-instruct at http://127.0.0.1:11434 | budget 20000 tokens

  [before_model_callback] ok: 0 spent + ~30 about to send <= budget 20000

=== model call 1 (event by 'log_agent') ===
  cost        : input 219 tokens, output 25 tokens   (run total so far: 244)
  model asked : read_server_log({"server": "fin-export-01"})
  --- ADK calls our function read_server_log('fin-export-01') -> 3,268,884 characters ---
  tool result : {"result": "2026-03-12T02:00:00Z fin-export-01 export-job INFO batch=0 rows=250 status=ok\n2026-03-12T02:00:01Z fin-export-01 export-job INFO batch=1  ... [3,308,897 characters]   <- ADK appended this to the session

  [before_model_callback] BUDGET: refused this model call: 244 spent + ~827328 about to send > budget 20000
  model said  : 'BUDGET: refused this model call: 244 spent + ~827328 about to send > budget 20000'   <- no tool request: ADK stops the loop

>>> model calls actually made (events with usage): 1   tokens this run: 244
```

It took 35 seconds on one run and 187 seconds on another, on the same machine. Most of
that is the 3 MB string being built and stored, not the model.

**What it proves.**

- **Same numbers as lesson 1.** Lesson 1 refused at "227 spent + ~827421 about to send". The
  ADK version refused at "244 spent + ~827328". The budget is the same check in a new place.
- **ADK gave the hook, not the rule.** The 20,000, the estimate and the refusal text are all
  ours. ADK has no setting for this. That is slide 11: "Not one, not in the form we built."
- **We decided what happens when it trips.** Here the callback returns a reply, and ADK
  treats it as if the model said it. Look at the line: "model said: BUDGET: refused...". The
  model said nothing. The run ends cleanly, with one model call made. A different team might
  raise an exception instead, like the call cap does. That is a judgement, and it is yours.

**The trap the room brings.** People assume the call cap from demo 2 protects the budget. It
does not. This run made one model call, well under any cap. The second call alone would have
been 827,000 tokens.

---

## Demo 4 — One file, two ADK versions

**What it shows.** The same file, run under ADK 2.8.0 and then 2.10.0, behaves differently
twice. Once it raises where it used to warn. Once it sends the model different words, with
no error at all. (The lesson's recorded trap, and the point of slide 14: pin, and upgrade on
purpose.)

**When in the lesson.** At slide 14, after "No error, no traceback, just an agent that quietly
gets multi-tenancy wrong." Part A also fits at slide 5 if you would rather show it there.

**Setup.** Both environments made (step 3 of "Before the session"). Ollama warm. You do not
need to activate either; the commands name the Python to use.

**What the trainer does.**

1. Run the old version:

   ```
   .venv-adk28\Scripts\python adk_invoice_agent.py upgrade
   ```

2. Run the new version, same file:

   ```
   .venv\Scripts\python adk_invoice_agent.py upgrade
   ```

3. Read part B of both outputs, one after the other. Then part C of both.

**What the room sees.** ADK 2.8.0:

```
google-adk 2.8.0 | model ollama_chat/qwen3:4b-instruct at http://127.0.0.1:11434 | same file, run under each installed version

--- A. run the agent on a session id we made up, never created ---
>>> SessionNotFoundError: Session not found: demo-session-1

--- B. write one message into a session the store has never heard of ---
  [log WARNING google_adk.google.adk.sessions.in_memory_session_service] Failed to append event to session made-up-123: app_name invoice_app not in sessions
>>> append_event returned normally
>>> is that message in the store now? no - there is no such session

--- C. an instruction with ${tenant_id}, and tenant_id='Northwind' in session state ---
  instruction the model received: 'You work for the tenant $Northwind. Answer in one short sentence.\n\nYou are an agent. Your internal name is "tenant_agent".'
  model said                    : '"Northwind"'
```

ADK 2.10.0:

```
google-adk 2.10.0 | model ollama_chat/qwen3:4b-instruct at http://127.0.0.1:11434 | same file, run under each installed version

--- A. run the agent on a session id we made up, never created ---
>>> SessionNotFoundError: Session not found: demo-session-1

--- B. write one message into a session the store has never heard of ---
>>> SessionNotFoundError: Session made-up-123 not found.
>>> is that message in the store now? no - there is no such session

--- C. an instruction with ${tenant_id}, and tenant_id='Northwind' in session state ---
  instruction the model received: 'You work for the tenant ${tenant_id}. Answer in one short sentence.\n\nYou are an agent. Your internal name is "tenant_agent".'
  model said                    : '"tenant_{tenant_id}"'
```

The model's sentence in part C varies from run to run. The instruction line does not. Every
recorded run is in the log.

**What it proves.**

- **Part B: from a warning to an exception.** On 2.8.0 the in-memory store logged a warning,
  returned normally, and threw the message away. On 2.10.0 the same call raises
  `SessionNotFoundError`. The ADK 2.9.0 release notes say this: "`InMemorySessionService` now
  raises `SessionNotFoundError` when an event is appended to a session it does not hold."
  The old behaviour was worse. It lost data in silence. The new one is a crash you can see.
- **Part C: the silent one.** The instruction is the only thing that changed. On 2.8.0 ADK
  filled `{tenant_id}` and left the `$`, so the model read `$Northwind`. On 2.10.0 ADK left
  `${tenant_id}` exactly as typed, and the model answered with nonsense. No error on either.
  The ADK 2.10.0 release notes: "leaves `${var}` and backslash-escaped `\{var}` as written
  instead of filling them from state." ADK's own syntax is `{tenant_id}`, with no dollar.
- **Pin, and upgrade in one sitting.** Nothing in this file changed between the two runs. Only
  the pin did.

**Say this carefully: part A is the same on both.** The speech (slide 5) says the in-memory
store "used to quietly accept work for a session it had never heard of". Part A shows that
ADK's `Runner` refused a made-up session id on 2.8.0 as well. The 2.6.3 source says the same.
What changed in 2.9.0 is the store underneath (part B). So say: "the runner always refused a
session you never created; the store under it used to swallow the write in silence, and now
it raises." That is accurate, and it still makes the slide's point.

**Also say carefully:** the speech says the old version showed the model "the tenant is
Northwind". It showed `$Northwind`, with the dollar sign. The old version was not right
either; it was just less wrong.

**The trap the room brings.** They expect an upgrade to fail loudly if it breaks something.
Part B does. Part C does not, and part C is the one that reaches a customer.
