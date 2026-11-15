# Lesson 1 — The agent loop, written by hand: demonstrations

Four demos. All four run one file, `invoice_agent.py`, against a real model.
No framework. No library to install. Python standard library only.

| # | Demo | Objective | Lands after |
|---|---|---|---|
| 1 | One turn, traced | 1.1 | Slide 10, "Five things in one trace" |
| 2 | The loop, and the step cap firing | 1.2 | Slide 12, "The cap on steps" |
| 3 | The budget refuses before it spends | 1.2 | Slide 13, "The budget, checked before you spend" |
| 4 | Three runs, three sentences, one set of facts | 1.3 | Slides 14 to 17 |

Every output quoted below was observed. The full, unedited output of every command is in
`invoice_agent_RUN_LOG.md`.

## Before the session (once, about five minutes)

1. Install Ollama from https://ollama.com and start it.
2. Pull the model. Do this the day before, not on conference wifi:

   ```
   ollama pull qwen3:4b-instruct
   ```

3. Warm the model up ten minutes before class, so the first demo is not slow:

   ```
   ollama run qwen3:4b-instruct "hello"
   ```

4. Open a terminal in this folder. Check that Python 3.10 or newer is there:

   ```
   python --version
   ```

5. Make the terminal font large. The trace lines are long.

The files in this folder:

- `invoice_agent.py` — the loop, three tools, and the four demo modes.
- `invoices.csv` — twelve invoices. This is the "finance database". Invoice 4471 is paid on
  2026-03-12. Invoice 4480 is unpaid.
- `invoice_agent_RUN_LOG.md` — what every command printed when it was run.

**Using a hosted model instead.** The program talks to any OpenAI-compatible
`/chat/completions` endpoint. Set three variables and nothing else changes:

```
AGENT_BASE_URL=https://api.openai.com/v1
AGENT_MODEL=<a model id your account can use>
AGENT_API_KEY=<your key>
```

This was only run against Ollama. Against a hosted provider it is unproven: the token
numbers, the wording and the timing will all differ from this document.

**If the model server dies mid-demo.** The loop does not crash. It prints
`outcome: MODEL_ERROR` and the network error. That happened twice while this was being
tested. Say what happened, run `ollama ps`, restart Ollama, and run the command again.

---

## Demo 1 — One turn, traced

**What it shows.** One real agent turn, with each step labelled: who decided, what ran,
under whose credentials, how many times round, and what it cost. (Objective 1.1.)

**When in the lesson.** After paragraph 37, on slide 10, "Five things in one trace". The
talk has just walked the invoice turn in words. Now the room watches the real one.

**Setup.** Ollama running with `qwen3:4b-instruct` pulled. Nothing else.

**What the trainer does.**

1. Say: "That was the story. Here is the same turn, for real, on this laptop."
2. Run:

   ```
   python invoice_agent.py trace
   ```

3. Point at the output line by line, in this order:
   - `=== step 1` and `sent : 2 messages, roles ['system', 'user']` — **who decided**: your
     program chose the model, the instructions and the tool. The model has said nothing yet.
   - `model asked : lookup_invoice({"invoice_number":4471})` — the model's one decision. It
     is a request. Nothing has run.
   - `--- our code runs lookup_invoice(...)` — **what ran**: your function, in your process.
   - `credentials : OS user '...'` — **whose credentials**: the account running the
     program. Not the model.
   - `reach : this account can read all 12 invoices ... the model named 1` — the hard
     question from slide 7.
   - `=== step 2` — **how many times round**: twice. Note the roles now include
     `assistant` and `tool`. The whole conversation went back.
   - The two `cost` lines — **what it cost**: input went from about 214 to about 317
     tokens. The second trip is bigger.
4. Open `invoice_agent.py` at line 27 and read the one line aloud:

   ```python
   body = {"model": MODEL, "messages": messages, "tools": tools, **options}
   ```

   Say: "That is everything the model ever receives. No password. No file. No database."

**What the room sees.** Observed on 2026-10-15 (the OS user, pid and the final sentence
will differ on your machine):

```text
model qwen3:4b-instruct | endpoint http://127.0.0.1:11434/v1 | step cap 10 | budget 20000 tokens | sampling model default

=== step 1: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 2 messages, roles ['system', 'user']
  cost        : input 214 tokens, output 24 tokens   (run total so far: 238)
  model asked : lookup_invoice({"invoice_number":4471})   <- the model decided; nothing has run yet
  --- our code runs lookup_invoice({'invoice_number': 4471}) ---
  credentials : OS user 'rtc', pid 1572 - this process's rights, not the model's
  reach       : this account can read all 12 invoices in invoices.csv; the model named 1
  result      : {"invoice_number": "4471", "customer": "Calder Engineering", "amount_eur": "2380.00", "status": "paid", "paid_on": "2026-03-12", "payment_reference": "PAY-88177"}

=== step 2: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 4 messages, roles ['system', 'user', 'assistant', 'tool']
  cost        : input 317 tokens, output 57 tokens   (run total so far: 612)
  model said  : 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount of EUR 2380.00 was settled with payment reference PAY-88177.'   <- no tool request: stop

>>> outcome: ANSWERED   steps: 2   tokens this run: 612
>>> tools run: [('lookup_invoice', {'invoice_number': 4471})]
>>> Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount of EUR 2380.00 was settled with payment reference PAY-88177.
```

It took 17 seconds on a CPU-only test machine.

**What it proves.** The model never touched the data. It sent one request. Your code ran it,
as you, with access to every invoice. The user saw one sentence; the bill saw two calls,
612 tokens, and the second call was bigger than the first.

The trap: the room expects the cost to be about the answer. The answer is about 57 output
tokens. The run cost 612. Most of what you pay for is input that you resend.

A note on cost: the model here is local, so no money changes hands. The token counts are
the real ones the endpoint returned. On a hosted model, multiply them by its price list.

---

## Demo 2 — The loop, and the step cap firing

**What it shows.** The whole loop fits on one screen, with its three limits in it from the
first version. Then a real run that never finishes hits the step cap and stops with a
readable failure. (Objective 1.2.)

**When in the lesson.** Two moments.
- Step 1 below goes with slide 11, "Forty lines and a stop condition", at paragraph 41.
- Steps 2 to 4 go after paragraph 53, at the end of slide 12, "The cap on steps".

**Setup.** As Demo 1.

**What the trainer does.**

1. At slide 11, open `invoice_agent.py` and scroll to line 41, `THE LOOP`. Read it top to
   bottom. It is 29 lines, from `THE LOOP` to `END OF THE LOOP`. With `call_model` (lines
   25 to 33) it is about forty. Point at the three comments:
   - line 45, `# LIMIT 2: the step cap`
   - line 47, `# LIMIT 3: budget, checked BEFORE`
   - line 57, `# LIMIT 1: the stop condition` — `if not reply.get("tool_calls"):`. Say: "This is
     the stop condition. It does not read the words. It checks whether there is a tool
     request."
2. At the end of slide 12, show the tool that never finishes. Open line 84,
   `check_settlement`. Say plainly: "This tool is a polling API that never settles. It
   always says IN_PROGRESS. Like the email in my opening story, the loop will never meet
   its stop condition if the model keeps asking."
3. Run:

   ```
   python invoice_agent.py runaway --max-steps 3
   ```

   The question it sends is: `On what date did the bank settle the payment for invoice
   4471? Keep checking until the settlement is final.`
4. While it runs, read the `cost` lines aloud as they appear: input 216, then 286, then
   397. Point at the `outcome: STEP_CAP` line at the end.

**What the room sees.** Observed on 2026-10-15:

```text
model qwen3:4b-instruct | endpoint http://127.0.0.1:11434/v1 | step cap 3 | budget 20000 tokens | sampling model default

=== step 1: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 2 messages, roles ['system', 'user']
  cost        : input 216 tokens, output 25 tokens   (run total so far: 241)
  model asked : check_settlement({"invoice_number":4471})   <- the model decided; nothing has run yet
  --- our code runs check_settlement({'invoice_number': 4471}) ---
  credentials : OS user 'rtc', pid 6884 - this process's rights, not the model's
  result      : {"invoice_number": 4471, "settlement": "IN_PROGRESS", "final": false, "detail": "bank confirmation not yet received"}

=== step 2: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 4 messages, roles ['system', 'user', 'assistant', 'tool']
  cost        : input 286 tokens, output 66 tokens   (run total so far: 593)
  model asked : check_settlement({"invoice_number":4471})   <- the model decided; nothing has run yet
  --- our code runs check_settlement({'invoice_number': 4471}) ---
  credentials : OS user 'rtc', pid 6884 - this process's rights, not the model's
  result      : {"invoice_number": 4471, "settlement": "IN_PROGRESS", "final": false, "detail": "bank confirmation not yet received"}

=== step 3: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 6 messages, roles ['system', 'user', 'assistant', 'tool', 'assistant', 'tool']
  cost        : input 397 tokens, output 66 tokens   (run total so far: 1056)
  model asked : check_settlement({"invoice_number":4471})   <- the model decided; nothing has run yet
  --- our code runs check_settlement({'invoice_number': 4471}) ---
  credentials : OS user 'rtc', pid 6884 - this process's rights, not the model's
  result      : {"invoice_number": 4471, "settlement": "IN_PROGRESS", "final": false, "detail": "bank confirmation not yet received"}

>>> outcome: STEP_CAP   steps: 3   tokens this run: 1056
>>> tools run: [('check_settlement', {'invoice_number': 4471}), ('check_settlement', {'invoice_number': 4471}), ('check_settlement', {'invoice_number': 4471})]
>>> agent did not finish within 3 steps
```

It took 41 seconds on the test machine.

**Why the cap is 3 and not 10.** The model does not always keep asking. With a cap of 5,
one test run polled five times and hit the cap. Another polled three times, then answered
in words that the settlement was still in progress, and stopped at step 4. The second run
is in the run log in full; the first is noted at the end of it. A cap of 3 fired on the run it was tried on, and three steps is inside the
"three or four is normal for a lookup" range the talk gives. If on the day the model gives
up before the cap, say so. It is the stop condition working, and it is the same lesson
the room is about to learn in Demo 4: the path through the loop changes between runs.

**What it proves.** A stop condition only fires on success. When the work never finishes,
only the counter stops the loop, and it stops with a readable failure, not a crash. The input
column grows every step — 216, 286, 397 — because each trip resends the whole conversation.

The trap: people reach for a better stop condition. The stop condition here is perfect. The
model simply never meets it.

---

## Demo 3 — The budget refuses before it spends

**What it shows.** A loop that runs only twice can still blow the budget, because one tool
result can be huge. The budget check runs before the call, so the expensive call is never
made. (Objective 1.2.)

**When in the lesson.** After paragraph 59, at the end of slide 13, "The budget, checked
before you spend". The talk has just said "checking before means the worst run you can
have is the budget you chose".

**Setup.** As Demo 1.

**What the trainer does.**

1. Open line 90, `read_server_log`. Say: "This tool returns a forty-thousand-line log. It
   builds it right here, so we all know exactly what is in it."
2. Run:

   ```
   python invoice_agent.py budget
   ```

3. Point at the result line, `[3,268,884 characters]`, then at the last line.
4. Point at lines 46 to 49 in the loop: the estimate is taken, compared, and the function
   returns before `call_model` is reached.

**What the room sees.** Observed on 2026-10-15:

```text
model qwen3:4b-instruct | endpoint http://127.0.0.1:11434/v1 | step cap 10 | budget 20000 tokens | sampling model default

=== step 1: call to the model (qwen3:4b-instruct at http://127.0.0.1:11434/v1) ===
  sent        : 2 messages, roles ['system', 'user']
  cost        : input 202 tokens, output 25 tokens   (run total so far: 227)
  model asked : read_server_log({"server":"fin-export-01"})   <- the model decided; nothing has run yet
  --- our code runs read_server_log({'server': 'fin-export-01'}) ---
  credentials : OS user 'rtc', pid 16816 - this process's rights, not the model's
  result      : 2026-03-12T02:00:00Z fin-export-01 export-job INFO batch=0 rows=250 status=ok
2026-03-12T02:00:01Z fin-export-01 export-job INFO batch=1 rows=250 stat ... [3,268,884 characters]

>>> outcome: BUDGET   steps: 1   tokens this run: 227
>>> tools run: [('read_server_log', {'server': 'fin-export-01'})]
>>> refused step 2: 227 spent + ~827421 about to send > budget 20000
```

It took 12 seconds on the test machine.

**What it proves.** The step cap was 10 and this run used one step. The step cap would never
have caught it. The budget did, and before the money was spent: 827,421 estimated tokens
were never sent.

Two honest notes for the room:
- The estimate is rough: about four characters per token (line 36). A provider's own
  token counter is more exact. For a gate, rough is enough.
- On this laptop, Ollama would not have charged anything. The Ollama docs say its context
  window defaults to 4k tokens on machines with under 24 GiB of VRAM. They do not say what
  happens to a request far bigger than that, and this demo never sends one, so that is
  untested. A hosted model would bill every input token it accepts. Either way, your
  budget check decides, not the server.

The trap: "a step cap is a cost cap". It is not. Count and size are different limits.

---

## Demo 4 — Three runs, three sentences, one set of facts

**What it shows.** The same code, question and model give different sentences on each run.
What stays the same — the tool, its argument, the fact, the date, the step count, the
tokens — can be asserted. (Objective 1.3.)

**When in the lesson.** In three steps, following the talk:
- Step 1 at paragraph 63, slide 14: "Now I am going to run our loop... three times in a row."
  Ask the room what they expect before pressing Enter.
- Step 2 after paragraph 75, slide 15, "Temperature, seeds, and no promise".
- Steps 3 and 4 at paragraphs 79 to 85, slides 16 and 17.

**Setup.** As Demo 1.

**What the trainer does.**

1. Ask the room: "Same question, same code, same model, three times. What do you expect?"
   Then run:

   ```
   python invoice_agent.py repeat 3
   ```

   Scroll to the block `the three sentences`. Read them aloud. Point at
   `identical strings: False`.
2. At slide 15, run:

   ```
   python invoice_agent.py repeat 3 --temperature 0 --seed 42
   ```

   Point at `identical strings: True`. Then say what this does **not** show: it is one
   laptop, serving one user, and one copy of a model file that will not change. It cannot
   show the shared-hardware effect or a model update from the talk. Those are the reasons
   it is not a promise on a hosted service.
3. At slide 16, go back to the first run's output. Ask the room: "What stayed the same?"
   Then scroll to `the facts and the path`. Every line is a PASS on three different
   sentences. Open line 149, `check_facts`, and read the checks aloud. None of them
   compares the sentence.
4. At slide 17, run the unpaid invoice:

   ```
   python invoice_agent.py repeat 3 --invoice 4480
   ```

   Point at `never says it was paid`. Say: "If this ever fails, it is not a flaky test. The
   agent was wrong."

**What the room sees.** Observed on 2026-10-15.

Step 1, `repeat 3` (69 seconds):

```text
================ the three sentences ================
run 1: 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The payment reference is PAY-88177.'
run 2: 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount of €2380.00 was settled with the payment reference PAY-88177.'
run 3: 'Yes, invoice 4471 has been paid. It was paid on 2026-03-12 for a total amount of €2380.00 by Calder Engineering.'
identical strings: False

================ the facts and the path ================
run 1: PASS  called lookup_invoice with 4471
run 1: PASS  touched no other tool
run 1: PASS  finished inside 10 steps
run 1: PASS  inside 20000 tokens
run 1: PASS  says it was paid
run 1: PASS  gives the date 12 March
```

(Runs 2 and 3 print the same six PASS lines. The three runs used 599, 612 and 600 tokens.)

Step 2, `repeat 3 --temperature 0 --seed 42` (51 seconds):

```text
================ the three sentences ================
run 1: 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount was €2380.00.'
run 2: 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount was €2380.00.'
run 3: 'Yes, invoice 4471 has been paid. It was paid on March 12, 2026, by Calder Engineering. The amount was €2380.00.'
identical strings: True
```

Step 4, `repeat 3 --invoice 4480` (41 seconds):

```text
================ the three sentences ================
run 1: 'No, invoice 4480 has not been paid. It is currently marked as "unpaid" and is due from Westmoor Clinic.'
run 2: 'No, invoice 4480 has not been paid. It is currently marked as "unpaid." The invoice is for Westmoor Clinic and amounts to €3120.00.'
run 3: 'No, invoice 4480 has not been paid. It is currently marked as "unpaid" and is still outstanding.'
identical strings: False
```

All 15 fact checks passed, and the command exited with code 0.

**What the talk says that this demo did not show.** Paragraph 67 says some runs call the
tool twice or take a different path. On the plain lookup question, every observed run with
`qwen3:4b-instruct` took the same path: one lookup, then an answer. The changing path was
seen in Demo 2 instead: the same runaway question gave five polls on one run and three on
another. Point back to it there. Do not claim it here unless it happens on the day.

**If the three sentences come out identical at default settings.** That happened once
during testing, with an earlier system prompt that ended in "Be brief." The model's own
defaults are narrow (temperature 0.7, top_p 0.8, top_k 20). If it happens on the day, run
it again, or add `--temperature 1`, and say so. `repeat 3 --temperature 1` was tried once
in testing and gave three different sentences. Three identical answers do not make a model
deterministic.

**Optional, if the room is sceptical that the hard-fact test can ever fail.** Run a smaller
model on the same check:

```
ollama pull llama3.2:3b
AGENT_MODEL=llama3.2:3b python invoice_agent.py repeat 3 --invoice 4480
```

(In PowerShell: `$env:AGENT_MODEL="llama3.2:3b"; python invoice_agent.py repeat 3 --invoice 4480`.)

In testing, `llama3.2:3b` once wrote the tool call as plain text instead of a tool request.
The loop saw no tool request and stopped, and the check `never says it was paid` failed on
that run. On the run recorded in the log, all its checks passed. So this may or may not
fail in front of the room. Present it as "this happens sometimes", which is exactly the
point of paragraph 85.

**What it proves.** The code did the same thing every time. The model did not. Temperature 0
and a seed reduced the variation here to nothing, on one machine, today. That is not a
guarantee. What you can test is the tool, its argument, the fact, the date, the steps and
the money — and those held on every run.

The trap: when the output changes, engineers conclude their code is broken. Point at the
identical PASS lines under three different sentences. Nothing in the code changed.
