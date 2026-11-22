# Lesson 3 — Tools are an interface: docstrings and schemas: demonstrations

Four demos. All four run one file, `tool_lab.py`, against a real model. No framework and
no library to install: Python standard library only. The model is the same local one as in
lessons 1 and 2.

| # | Demo | Objective | Lands after |
|---|---|---|---|
| 1 | The tool the model will not call, repaired one line at a time | 2.1, both halves | Slides 4, 5, 6 and 7 |
| 2 | A fixed list, and a field that should not be required | 2.1, "call it correctly" | Slides 8 and 9 |
| 3 | The tool ran, and the model still said "not found" | 2.1, "call it correctly" | Slide 10 |
| 4 | Shouting in the system prompt | 2.1, "repair a tool the model refuses to call" | Slide 11 |

Objective 2.1, word for word: *Write a tool whose docstring and schema make the model call
it correctly, and repair a tool the model refuses to call.*

Every output quoted below was seen on this machine on 2026-10-15. The full, unedited output
of every command is in `tool_lab_RUN_LOG.md`.

Slide 12, "Three ways it goes wrong", gets no demo of its own. The room will already have
seen all three ways. Point back to them:

- **Never called:** demo 1, step A.
- **Called with bad arguments:** demo 1, steps B and C, and demo 2.
- **Called, but the answer was not understood:** demo 3.

Slide 13 (overlapping tools) gets no demo. Four is enough for one lesson, and the token
cost it mentions is already on screen in demo 1.

## Before the session (once, about five minutes)

1. Ollama running, with the lesson 1 model pulled. Do this the day before:

   ```
   ollama pull qwen3:4b-instruct
   ```

2. Warm the model up ten minutes before class:

   ```
   ollama run qwen3:4b-instruct "hello"
   ```

3. Open a terminal in this folder. Check that Python 3.10 or newer is there:

   ```
   python --version
   ```

4. Make the terminal font large. The tool definitions are long. Scroll up to show them.

**The files in this folder:**

- `tool_lab.py` is the program. It loads one file of plain Python functions from
  `tools/`. It turns them into tool definitions and prints exactly what the model is sent.
  Then it runs the loop and answers three questions for each run: did it call, did it call
  correctly, and what did it say.
- `tools/` holds one file per step. Each file differs from the one before by the change
  its first line names. Every file gives the agent three tools:
  - the invoice tool, which is the one that changes;
  - `list_supplier_invoices`, from `tools/common.py`;
  - `get_supplier_contact`, from `tools/common.py`.
- `invoice_db.py` reads `invoices.csv` and `suppliers.csv`. It records every query and how
  many rows matched. That is how "did it call correctly?" is answered from what the
  database actually saw.
- `invoices.csv` holds twelve supplier invoices. Numbers are stored as `INV-4471`.
  INV-4471 (Calder Engineering) was paid on 2026-03-12. Nordwind GmbH has two invoices:
  INV-4467, €9,200, overdue, and INV-4469, paid. Orbis Retail's INV-4470 is overdue.
- `suppliers.csv` holds one accounts contact per supplier. The names and emails are made up.
- `tool_lab_RUN_LOG.md` is what every command printed.

**How the definitions are built.** The block marked `WHAT A FRAMEWORK DOES WITH YOUR
FUNCTION` in `tool_lab.py` does what Google's ADK documentation describes:

- the function name becomes the tool name;
- the type hints become the schema types;
- the docstring becomes the description;
- each `Args:` line becomes a parameter description;
- a parameter with no default becomes required.

It is about 40 lines, written here so the room can read it. Lesson 4 shows a framework
doing the same thing.

**Timing.** On the test machine (CPU only), one model call took 3 to 41 seconds. Nine
in ten took under 14 seconds; the long ones were answers that listed several invoices.
One command with `--runs 3` took 23 to 129 seconds. Use `--runs 1` if time is short.
Three runs is what shows the room it was not luck.

**Your run may differ.** The model is not deterministic (lesson 1). Most steps gave the
same behaviour in all three runs here. Demo 4 did not, and that is part of its point. Run
every command once on the class laptop the day before.

**Using a hosted model instead.** Set three variables and nothing else changes:

```
AGENT_BASE_URL=https://api.openai.com/v1
AGENT_MODEL=<a model id your account can use>
AGENT_API_KEY=<your key>
```

This was only run against Ollama. Against a hosted provider it is unproven. A stronger
model may call even the vague tool. If it does, demo 1 step A will not refuse, and the
demo loses its opening.

**If the model server is down**, the program prints `MODEL_ERROR: cannot reach ...` and
exits. Restart Ollama and run the command again.

---

## Demo 1 — The tool the model will not call, repaired one line at a time

**What it shows.** The story from slide 1, live. The function works, the model refuses
it, and the fix is in the words, not the code. The name brings the call back. The
parameter's format example makes the call correct. (Objective 2.1, both halves.)

**When in the lesson.**

- Step A: at the end of slide 4, after "Now a lazy comment is a bug."
- Step B: at slide 5, after "Start with the name".
- Step C: at slide 6.
- Step D: at slide 7, after "an example beats an explanation".

**Setup.** As above. Nothing else.

**What the trainer does.**

1. Open `tools/t1_run_query.py`. Show that the code is fine: it finds the row and returns
   it. Read the docstring aloud: `"""Queries the system."""`
2. Run:

   ```
   python tool_lab.py tools/t1_run_query.py "Has invoice 4471 been paid?" --runs 3
   ```

3. Scroll to the top of the output. Say: "This is everything the model knows about my
   function." Point at `"description": "Queries the system."` and at `"ref"`, which has no
   description. Then point at the two other tools, which are well described.
4. Point at the token line, `(about 308 tokens, sent again on every call of the loop)`,
   and at `input 417 tokens` on each step.
5. Scroll down. Read one refusal aloud. Point at `>>> tool called in 0 of 3 run(s)`.
6. At slide 5, open `tools/t2_renamed.py`. One change: the function is now
   `get_invoice_status(invoice_number: str)`. The docstring is still "Queries the system."
   Run:

   ```
   python tool_lab.py tools/t2_renamed.py "Has invoice 4471 been paid?" --runs 3
   ```

   Point at `tool called in 3 of 3`. Then point at line 2 of the questions:
   `invoice_number == '4471' -> 0 row(s)`.
7. At slide 6, open `tools/t3_described.py`. The docstring now says what the tool does,
   when to use it, and when not to. Run:

   ```
   python tool_lab.py tools/t3_described.py "Has invoice 4471 been paid?" --runs 3
   ```

   Ask the room: "Did the description fix it?" It did not. The model still sends `4471`.
8. At slide 7, open `tools/t4_format.py`. One more line, under `Args:`:
   `invoice_number: The invoice number as printed on the invoice, in the form INV-4471.`
   Run:

   ```
   python tool_lab.py tools/t4_format.py "Has invoice 4471 been paid?" --runs 3
   ```

   Point at `"INV-4471"` in the call, `1 row(s)`, and the answer. Then compare
   `input 484 tokens` with step A's `input 417`.

**What the room sees.** Observed.

Step A. The definition the model is sent for the invoice tool:

```text
      "name": "run_query",
      "description": "Queries the system.",
      "parameters": {
        "type": "object",
        "properties": {
          "ref": {
            "type": "string"
          }
        },
        "required": [
          "ref"
        ]
```

Then the three runs:

```text
--- run 1 of 3 ---
  step 1 (8.3s, input 417 tokens)
    model answered : "I cannot determine if invoice 4471 has been paid as the available functions do not allow querying an invoice by its number. You may need to provide more context or check with the relevant accounts records directly. Let me know if you'd like help with something else!"
  1. Did it call the tool?      NO
...
>>> tool called in 0 of 3 run(s)
```

All three runs refused, in slightly different words. This is the developer's two days: a
working function, and an agent that says it cannot look invoices up.

Step B. The name alone brought the call back, three runs out of three. Every call sent the
wrong thing:

```text
    model asked    : get_invoice_status({"invoice_number":"4471"})
    our code ran it: returned '{"status": "not_found", "message": "No invoice exists with number 4471."}'
  step 2 (9.0s, input 480 tokens)
    model answered : 'The invoice with number 4471 was not found in the system. It may be incorrect or missing. Please verify the invoice number and try again.'
  1. Did it call the tool?      YES: get_invoice_status
  2. Did it call it correctly?  get_invoice_status({"invoice_number":"4471"}) -> database saw: invoice_number == '4471' -> 0 row(s)
```

Step C. The same, three out of three: `"4471"`, 0 rows, and "There is no invoice with the
number 4471 in the system." The when-and-when-not description did not change the
argument. The step 2 timing line is in the log.

Step D. Three out of three:

```text
    model asked    : get_invoice_status({"invoice_number":"INV-4471"})
    our code ran it: returned '{"status": "ok", "invoice": {"invoice_number": "INV-4471", "supplier": "Calder Engineering", "amount_eur": "2380.00", "status": "paid", "due_date": "2026-03-14", "paid_on": "2026-03-12"}}'
...
    model answered : 'Yes, invoice INV-4471 from Calder Engineering has been paid. The amount of €2,380.00 was paid on March 12, 2026, which was before its due date of March 14, 2026.'
  1. Did it call the tool?      YES: get_invoice_status
  2. Did it call it correctly?  get_invoice_status({"invoice_number":"INV-4471"}) -> database saw: invoice_number == 'INV-4471' -> 1 row(s)
```

The token count on step 1 went from 417 (step A) to 484 (step D). The better description
costs 67 input tokens on every call.

**What it proves.**

- The model never saw the code. Four short text changes, and no logic change, took it from
  refusing to answering correctly.
- **The name** brought the call back.
- **The format example** made the call correct.
- **The description** changed nothing visible on this question. Say that plainly: it earns
  its place in demo 2, where there are two similar tools.

**The trap.** The room expects the first fix to be "better description". Here the name did
more than the description. The room also expects that once the tool is called, the bug is
fixed. Steps B and C show it is not. The model called the tool, got nothing back, and told
the user, three times in a row, that invoice 4471 does not exist. That is worse than a
refusal, because it looks like an answer.

---

## Demo 2 — A fixed list, and a field that should not be required

**What it shows.** Two schema decisions change the answer to a business question.

- A status written in prose gets made-up values. A fixed list gets real ones.
- A required field the user never mentioned gets a made-up value, and half the data goes
  missing.

(Objective 2.1: a schema that makes the model call it correctly.)

**When in the lesson.** Steps A and B at slide 8, "A fixed list beats prose". Steps C and
D at slide 9, after "so it filled the field".

**Setup.** As above.

**What the trainer does.**

1. Open `tools/s1_loose_list.py`. The list tool's `status` is `str`, it is required, and
   it is described as "The payment status of the invoices." Ask the room what values the
   database has. Answer: `paid`, `unpaid`, `overdue`. The model is not told.
2. Run:

   ```
   python tool_lab.py tools/s1_loose_list.py "Which Orbis Retail invoices are late?" --runs 3
   ```

3. Open `tools/s2_tight_list.py`. It uses the version in `tools/common.py`:
   `status: Literal["paid", "unpaid", "overdue"] | None = None`. Run:

   ```
   python tool_lab.py tools/s2_tight_list.py "Which Orbis Retail invoices are late?" --runs 3
   ```

   Scroll up and point at the `"enum"` in the definition. `Literal` became it.
4. At slide 9, ask a question that names no status at all, first against the loose tool:

   ```
   python tool_lab.py tools/s1_loose_list.py "Which invoices do we have from Nordwind GmbH?" --runs 3
   ```

5. Then against the tight one:

   ```
   python tool_lab.py tools/s2_tight_list.py "Which invoices do we have from Nordwind GmbH?" --runs 3
   ```

**What the room sees.** Observed.

Step 2 (loose, "late"), three out of three:

```text
    model asked    : list_supplier_invoices({"supplier":"Orbis Retail","status":"late"})
    our code ran it: returned '{"status": "not_found", "message": "No invoices found for supplier \'Orbis Retail\' with status \'late\'."}'
...
    model answered : 'There are no late invoices from Orbis Retail.'
```

That is false. INV-4470, €4,410, is overdue.

Step 3 (fixed list, "late"), three out of three:

```text
    model asked    : list_supplier_invoices({"supplier":"Orbis Retail","status":"overdue"})
...
  2. Did it call it correctly?  list_supplier_invoices({"supplier":"Orbis Retail","status":"overdue"}) -> database saw: supplier == 'Orbis Retail' and status == 'overdue' -> 1 row(s)
```

The answer names INV-4470, €4,410.00, due 15 March 2026.

Step 4 (status required, user never gave one), three out of three. The model invented
`paid`:

```text
    model asked    : list_supplier_invoices({"supplier":"Nordwind GmbH","status":"paid"})
...
    model answered : 'We have one invoice from Nordwind GmbH:\n\n- **Invoice Number**: INV-4469\n- **Amount**: €1290.00\n- **Status**: Paid\n- **Due Date**: 2026-03-12\n- **Paid On**: 2026-03-09\n\nLet me know if you need any further details!'
```

"We have one invoice." There are two. The one it hid is the €9,200 overdue one.

Step 5 (status optional), three out of three. The model left status out:

```text
    model asked    : list_supplier_invoices({"supplier":"Nordwind GmbH"})
...
  2. Did it call it correctly?  list_supplier_invoices({"supplier":"Nordwind GmbH"}) -> database saw: supplier == 'Nordwind GmbH' -> 2 row(s)
```

The answer lists both invoices, INV-4467 overdue and INV-4469 paid.

During the build, the same loose tool was also asked about Orbis Retail's "outstanding"
and "still open" invoices. It sent `"outstanding"` and `"open"`, matched nothing, and
answered "no" each time. Those runs are not in the run log.

**What it proves.**

- Prose in a parameter description is a guess for the model, and a wrong guess comes back
  as a confident "no". The fixed list turned the user's word "late" into the database's
  word `overdue`.
- A required field gets filled whether or not the user said anything. Here, filling it
  hid the most expensive invoice.

**Be straight with the room about two things.**

- `s2` changes three things at once compared with `s1`: the `enum`, the default that makes
  status optional, and the docstring wording. The lab is where they separate them one line
  at a time.
- Ollama passes the `enum` to the model. Its documentation does not say it enforces it.
  The model is *offered* three values; nothing here *forces* them. OpenAI documents a
  `strict: true` mode that does make the arguments follow the schema. Your function should
  still check its inputs either way.

---

## Demo 3 — The tool ran, and the model still said "not found"

**What it shows.** The third failure: the tool was called correctly and found the row,
but it returned something the model cannot read. (Objective 2.1: call it correctly, and
get an answer the model can use.)

**When in the lesson.** Slide 10, "What the tool sends back", after "a small dictionary
with a status key and a plain message works well."

**Setup.** As above.

**What the trainer does.**

1. Open `tools/r1_bad_return.py`. The name, the docstring and the schema are the same as
   `t4_format.py` from demo 1. Only the return changed. A found invoice comes back as an
   `Invoice` object. A missing one comes back as `None`.
2. Run:

   ```
   python tool_lab.py tools/r1_bad_return.py "Has invoice 4471 been paid?" --runs 3
   ```

3. Point at the call: correct, `INV-4471`. Point at what came back. Read the answer aloud.
4. Remind the room that demo 1, step D was the same question against the same tool,
   returning a dictionary, and the answer was right.
5. Optional, if there is time:

   ```
   python tool_lab.py tools/r1_bad_return.py "Has invoice INV-4499 been paid?" --runs 3
   ```

**What the room sees.** Observed. Step 2, three out of three:

```text
    model asked    : get_invoice_status({"invoice_number":"INV-4471"})
    our code ran it: returned '<r1_bad_return.Invoice object at 0x000001C0CBD07620>'
...
    model answered : "I couldn't retrieve the status for invoice 4471. It's possible that the invoice number is incorrect or the invoice doesn't exist in our records. Let me know if you'd like to try another invoice number or if you need assistance with something else."
...
  2. Did it call it correctly?  get_invoice_status({"invoice_number":"INV-4471"}) -> database saw: invoice_number == 'INV-4471' -> 1 row(s)
```

The database found the invoice. The model told the user it might not exist. Run 3 said
"the provided data is incomplete or corrupted."

Step 5 (`None`), three out of three: "The invoice with number INV-4499 could not be found
in the system. Please verify the invoice number and try again." Be honest about this one.
On this model, a bare `None` did *not* go wrong; the model read it as "not found". The
talk's point stands: you cannot know in advance what a model does with `None`. But this
run does not show it failing. The object did.

**What it proves.** "Did it call?" and "did it call correctly?" can both be yes, and the
agent still fails. The return value is part of the interface. A dictionary with a status
gave the right answer three times. An object's default text gave a wrong one three times.

**What the program does with a return value.** `tool_lab.py` sends dictionaries as JSON
and anything else as `str(value)`. Many hand-written loops do the same. ADK's
documentation says it wraps a non-dictionary return in `{"result": ...}`, and it
recommends returning a dictionary with a `status` key. What a given framework does with a
Python object was not tested here.

---

## Demo 4 — Shouting in the system prompt

**What it shows.** The tempting fix for a tool the model refuses: an order in capitals in
the system prompt, with the tool's description left vague. It is unreliable. When it does
work, the call is still wrong. (Objective 2.1: repair a tool the model refuses to call,
by the description and not by shouting.)

**When in the lesson.** Slide 11, after "YOU MUST ALWAYS USE THE INVOICE TOOL."

**Setup.** As above. This is the vague tool from demo 1, step A, again.

**What the trainer does.**

1. Run the step A command again, adding the shout to the system prompt:

   ```
   python tool_lab.py tools/t1_run_query.py "Has invoice 4471 been paid?" --runs 3 --system "You are an assistant for the accounts team. Answer the user's question. YOU MUST ALWAYS USE THE INVOICE TOOL."
   ```

2. Count the calls with the room. Read one answer aloud.
3. Then ask about something that is not an invoice, with the same shout:

   ```
   python tool_lab.py tools/t1_run_query.py "Who is our contact at Nordwind GmbH?" --runs 3 --system "You are an assistant for the accounts team. Answer the user's question. YOU MUST ALWAYS USE THE INVOICE TOOL."
   ```

**What the room sees.** Observed, and it differed between two runs of the same command.

In the logged run, step 1 got `>>> tool called in 0 of 3 run(s)`. One refusal even told
the user to do the work:

```text
    model answered : "I cannot check the payment status of a specific invoice (like invoice 4471) because the available tools do not support querying individual invoices by number. I recommend using the invoice tool to check that specific invoice. Let me know if you'd like me to assist further!"
```

In an earlier run of the identical command, the shout got one call in three, and that
call was wrong (in the run log's appendix):

```text
    model asked    : run_query({"ref":"4471"})
    our code ran it: returned '{"status": "not_found", "message": "No invoice exists with number 4471."}'
  step 2 (7.7s, input 536 tokens)
    model answered : 'There is no invoice with the number 4471 in the system.'
```

Step 3: the contact question went to `get_supplier_contact` three times out of three, and
the answer was right (Jonas Weber). The shout did **not** pull the unrelated question onto
the invoice tool.

**What it proves.**

- Shouting is not a repair. It got between zero and one calls in three, and the one call
  it got sent `4471` and told the user the invoice does not exist.
- The four words of description from demo 1 got three correct calls out of three.
- Fix *when* to call a tool in the tool's description, not in the system prompt.

**What this does not prove.** The talk says shouting also makes the model use the tool for
unrelated questions: purchase orders, suppliers, last month's total. That was **not** seen
here. With this model and these three tools, the unrelated question went to the right
tool. Do not claim the over-firing from this demo. Say it is the risk the talk describes,
and that this small model did not show it on this run.

---

## Assumptions

- The same local model as lessons 1 and 2, `qwen3:4b-instruct` on Ollama, so that nothing
  new is installed for this lesson. The refusal in demo 1, step A depends on it.
- The agent has three tools, not one. A real agent rarely has only one. With the vague
  tool alone, while this was being built, the model called it with `"invoice 4471 status"`
  rather than refusing. Those runs are not in the run log. With two well-described tools
  beside it, it refused three times out of three.
- The story's tool needed a database format the model could get wrong. So invoice numbers
  are stored as `INV-4471`, as the talk's format example suggests.
- One file per step, rather than editing the docstring live, so each step is one command
  and cannot be mistyped in front of the room. A trainer who prefers to edit live can copy
  `tools/t1_run_query.py` and make the same changes; the program reloads the file on every
  run.
