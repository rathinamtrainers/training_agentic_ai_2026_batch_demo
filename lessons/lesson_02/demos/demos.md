# Lesson 2 — Structured output, and when not to use an agent: demonstrations

Four demos. All four run one file, `structured.py`, against a real model. The only library
is Pydantic. The model is the same local one as lesson 1.

| # | Demo | Objective | Lands after |
|---|---|---|---|
| 1 | A sentence, then a record | 1.4 | Slide 3, "A contract, not a request" |
| 2 | Shape held, truth not: the second layer, the retry, the tray for a human | 1.4 | Slides 4, 6, 7 and 8 (start it at the end of slide 6) |
| 3 | Cut off, and the run that stops itself | 1.4 | Slide 8, "Set aside, or stop the run" |
| 4 | Just write the function, then one bounded call | 1.7 | Slide 10, then slide 15 |

Every output quoted below was seen on this machine on 2026-10-15. The full, unedited
output of every command is in `structured_RUN_LOG.md`.

The third sorting case, the agent, gets no new demo. The room watched a real agent loop in
lesson 1 (`../../lesson_01/demos/`). Point back to it at slide 14.

## Before the session (once, about five minutes)

1. Ollama running, with the lesson 1 model pulled. Do this the day before:

   ```
   ollama pull qwen3:4b-instruct
   ```

2. Open a terminal in this folder. Make the environment and install Pydantic:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   On macOS or Linux the second line is `source .venv/bin/activate`.

3. Warm the model up ten minutes before class:

   ```
   ollama run qwen3:4b-instruct "hello"
   ```

4. Make the terminal font large. The JSON lines are long.

The files in this folder:

- `structured.py` — the program. Five modes, one per step below.
- `invoices/` — six supplier invoices as text, in six different layouts. Two of them
  have a real error printed on the paper: `inv_3310_mehta.txt` (the total does not add
  up) and `inv_5120_ravi.txt` (the year is 2062).
- `system_invoices/` — three invoices from one supplier, all in the same fixed layout.
- `messages.txt` — five customer WhatsApp messages in Hinglish.
- `structured_RUN_LOG.md` — what every command printed.
- `out/` — written by the batch runs. Open `out/invoices.csv` in Excel if you want the room
  to see the spreadsheet.

**Timing.** On the test machine (CPU only, shared) one call took 15 to 80 seconds. Demo 2
took about five minutes. A laptop with a GPU is much faster, but that was not measured. Run
every demo once on the class laptop the day before and note the times.

**Using a hosted model instead.** The program talks to any OpenAI-compatible
`/chat/completions` endpoint. It sends `response_format` with
`{"type": "json_schema", ..., "strict": true}`. Set three variables:

```
AGENT_BASE_URL=https://api.openai.com/v1
AGENT_MODEL=<a model id your account can use>
AGENT_API_KEY=<your key>
```

This was only run against Ollama. Against a hosted provider it is unproven.

**If the model server is down**, the program prints `MODEL_ERROR: cannot reach ...` and
exits. Restart Ollama and run the command again.

---

## Demo 1 — A sentence, then a record

**What it shows.** The same job twice. First the model writes English and the program can
do nothing with it. Then a Pydantic class travels with the request, and the reply becomes
an object the program uses directly. (Objective 1.4: produce structured output.)

**When in the lesson.** Step 1 after paragraph 4, at the end of slide 1, "The sad text
parser". Steps 2 to 4 after paragraph 17, at the end of slide 3, "A contract, not a
request".

**Setup.** As above. Nothing else.

**What the trainer does.**

1. At the end of slide 1, say: "Here is invoice 4471, asked for in plain English." Run:

   ```
   python structured.py prose invoices/inv_4471_sharma.txt
   ```

   Point at the last two lines: `type(reply) = str` and the `AttributeError`. Then read
   the model's "Note" aloud and ask the room if it is true.
2. At the end of slide 3, open `structured.py` at line 60, `class Invoice`. Read the six
   fields. Say: "Six lines. This is the form."
3. Show line 38, `# THE CONTRACT TRAVELS WITH THE REQUEST`. The class goes into the
   request as `response_format`.
4. Run it on invoice 4472, the "breaks my parser" layout from the talk:

   ```
   python structured.py extract invoices/inv_4472_sharma.txt
   ```

   Point at three things, in order: the schema line at the top, the JSON that came back,
   and line 132, `Invoice.model_validate_json(content)`. Then `invoice.date.month = 3`.

**What the room sees.** Step 1, observed:

```text
model qwen3:4b-instruct | no schema | 46.1s | tokens in 250 out 140

--- what came back (a string) ---
Here is the extracted information from the invoice:

- **Supplier**: Sharma Traders  
- **Invoice Number**: 4471  
- **Date**: 12 March 2026  
- **Amount (Total Payable)**: ₹42,000.00  
- **Tax (GST @ 18%)**: ₹6,406.78  

✅ Note: The invoice date is listed as **12 March 2026**, which is in the future. This may be an error or a placeholder, but it is what is stated in the invoice.  

All details have been accurately extracted from the provided invoice.

--- what the program can do with it ---
type(reply) = str
reply.amount -> AttributeError: 'str' object has no attribute 'amount'
```

The model said 12 March 2026 is "in the future". It is not; this ran on 2026-10-15. Nobody
asked for that sentence. Your wording may differ; check what the model says before you
point at it.

Step 4, observed:

```text
--- the schema that travels with the request (from the Invoice class) ---
{"additionalProperties": false, "description": "One supplier invoice. All amounts in rupees.", "properties": {"supplier": {"title": "Supplier", "type": "string"}, "invoice_number": {"title": "Invoice Number", "type": "string"}, "date": {"format": "date", "title": "Date", "type": "string"}, "subtotal": {"title": "Subtotal", "type": "number"}, "tax": {"title": "Tax", "type": "number"}, "amount": {"title": "Amount", "type": "number"}}, "required": ["supplier", "invoice_number", "date", "subtotal", "tax", "amount"], "title": "Invoice", "type": "object"}

model qwen3:4b-instruct | 65.9s | tokens in 143 out 79 | finish_reason=stop

--- what came back ---
{
  "amount": 11800.0,
  "date": "2026-03-13",
  "invoice_number": "4472",
  "subtotal": 10000.0,
  "supplier": "Sharma Traders",
  "tax": 1800.0
}

--- invoice = Invoice.model_validate_json(reply) ---
Invoice(supplier='Sharma Traders', invoice_number='4472', date=datetime.date(2026, 3, 13), subtotal=10000.0, tax=1800.0, amount=11800.0)
invoice.date.month         = 3
invoice.subtotal * 0.18    = 1800.00
spreadsheet row            = ['Sharma Traders', '4472', '2026-03-13', 11800.0, 1800.0]
```

**What it proves.** `13.03.2026` on the paper came back as a real `datetime.date`. No
parser was written. The schema has `"required"` listing every field and
`"additionalProperties": false`. Pydantic wrote that from the class
(`extra="forbid"`). Strict mode on hosted providers demands both.

The talk uses `invoice.amount * 0.18` as its example. The program prints
`invoice.subtotal * 0.18`, because in this class `amount` already includes tax. The point
is the same: ordinary arithmetic on an ordinary object.

The trap: people think "reply in JSON" in the prompt is the same thing. It is not. Here
the shape is part of the request, not a polite line in the prompt.

---

## Demo 2 — Shape held, truth not: the second layer, the retry, the tray for a human

**What it shows.** A batch of six invoices. Every reply has a valid shape. Two are still
wrong, and only our own validators notice. The program sends the error back once, then
sets the invoice aside for a person. It does not crash. (Objective 1.4: validate against a
schema, and handle a validation failure.)

**When in the lesson.** Start it after paragraph 31, at the end of slide 6, "The subset,
and two layers". It runs for a few minutes. Talk slides 7 and 8 over it, and point at the
output as each invoice lands. It also pays off slide 4, "Shape is promised, truth is not".

**Setup.** As Demo 1.

**What the trainer does.**

1. Open `structured.py` at line 71, `the meaning (layer 2)`. Read the four rules in
   `business_rules`: amount positive, tax between zero and the total, date not in the
   future, subtotal plus tax equals the total. Say: "None of these are in the schema we
   send. They run in our code, after the object comes back."
2. Show line 164, `# retry DIFFERENTLY: send the error back`. Say: "One retry. It carries
   the error. Then we stop."
3. Run:

   ```
   python structured.py batch invoices
   ```

4. When `inv_3310_mehta.txt` fails, stop and read the reply aloud. Every field has the right
   type. Then read the paper: `cat invoices/inv_3310_mehta.txt` (`type` in cmd). The
   total on the paper is 49,560. It should be 4,956.
5. At the last line, open `out/set_aside.csv`. That is Friday morning's pile.

**What the room sees.** Observed:

```text
model qwen3:4b-instruct | 6 invoices | retries 1 | max_tokens None | stop if failure rate > 50% after 3 invoices

[inv_3310_mehta.txt]
    call 1: 21.6s, finish_reason=stop, reply: {   "amount": 49560,   "date": "2026-03-18",   "invoice_number": "3310",   "subtotal": 4200,   "supplier": "MEHTA OFFICE SUPPLIES",   "tax": 756.00 }
    validation failed: invoice: Value error, subtotal 4200.0 + tax 756.0 = 4956.00, but amount is 49560.0
    call 2: 20.1s, finish_reason=stop, reply: {   "amount": 49560,   "date": "2026-03-18",   "invoice_number": "3310",   "subtotal": 4200,   "supplier": "MEHTA OFFICE SUPPLIES",   "tax": 756.00 }
    validation failed: invoice: Value error, subtotal 4200.0 + tax 756.0 = 4956.00, but amount is 49560.0
  -> SET_ASIDE  invoice: Value error, subtotal 4200.0 + tax 756.0 = 4956.00, but amount is 49560.0
[inv_4471_sharma.txt]
    call 1: 34.4s, finish_reason=stop, reply: {   "amount": 42000,   "date": "2026-03-12",   "invoice_number": "4471",   "subtotal": 35593.22,   "supplier": "SHARMA TRADERS",   "tax": 6406.78 }
  -> OK         SHARMA TRADERS | 4471 | 2026-03-12 | 42000.0
[inv_4472_sharma.txt]
    call 1: 15.5s, finish_reason=stop, reply: {   "amount": 11800.0,   "date": "2026-03-13",   "invoice_number": "4472",   "subtotal": 10000.0,   "supplier": "Sharma Traders",   "tax": 1800.0 }
  -> OK         Sharma Traders | 4472 | 2026-03-13 | 11800.0
[inv_5120_ravi.txt]
    call 1: 22.1s, finish_reason=stop, reply: {   "amount": 10620,   "date": "2062-03-12",   "invoice_number": "5120",   "subtotal": 9000,   "supplier": "RAVI ELECTRICALS",   "tax": 1620 }
    validation failed: invoice: Value error, date 2062-03-12 is in the future
    call 2: 20.1s, finish_reason=stop, reply: {   "amount": 10620,   "date": "2062-03-12",   "invoice_number": "5120",   "subtotal": 9000,   "supplier": "RAVI ELECTRICALS",   "tax": 1620 }
    validation failed: invoice: Value error, date 2062-03-12 is in the future
  -> SET_ASIDE  invoice: Value error, date 2062-03-12 is in the future
[inv_88_gupta.txt]
    call 1: 73.9s, finish_reason=stop, reply: {   "amount": 5900,   "date": "2026-03-21",   "invoice_number": "88/2026",   "subtotal": 5000,   "supplier": "M/s Gupta Hardware & Sons",   "tax": 900 }
  -> OK         M/s Gupta Hardware & Sons | 88/2026 | 2026-03-21 | 5900.0
[inv_A2291_kaveri.txt]
    call 1: 81.5s, finish_reason=stop, reply: {   "amount": 118000,   "date": "2026-04-02",   "invoice_number": "A-2291",   "subtotal": 100000,   "supplier": "KAVERI PACKAGING INDUSTRIES",   "tax": 18000 }
  -> OK         KAVERI PACKAGING INDUSTRIES | A-2291 | 2026-04-02 | 118000.0

>>> 4 in the spreadsheet, 2 set aside for a human, 0 not attempted | 8 model calls, 2127 tokens
>>> wrote C:\Users\rtc\trainings\training_agentic_ai_2026_batch_research\012_curriculum\lessons\lesson_02\demos\out\invoices.csv and C:\Users\rtc\trainings\training_agentic_ai_2026_batch_research\012_curriculum\lessons\lesson_02\demos\out\set_aside.csv
```

Four different layouts were read correctly. That includes lakh notation (`1,18,000.00`
became `118000`) and a scrawled cash receipt (`dt 21-3-26` became `2026-03-21`).

**What it proves.**

- **Shape is not truth.** The Mehta reply passed the shape. It is a perfect `Invoice`. Its
  total is wrong by a factor of ten. Only the business rule caught it.
- **Two layers, two jobs.** The schema got the shape there. The validator checked the
  meaning.
- **The retry was capped, and here it was right not to help.** Both times the model sent
  back the same object, because the paper really says 49,560 and 2062. The model copied the
  paper. It did not invent a "better" number to pass the check. A retry cannot fix bad
  data, and an uncapped retry would have kept paying to repeat it. That is why the cap is
  there.
- **Set aside, not crash.** Four rows went into the spreadsheet. Two went to a person,
  with the reason attached.

The trap: the room expects the model to be the one that is wrong. Here the paper was
wrong, the model was faithful, and the validator is what saved the spreadsheet.

Not seen in this run: a retry that **succeeds** because the model fixed its own mistake
after reading the error. The talk says that often works. On this model and these
invoices the first reply was never malformed, so that path was not exercised. Do not
claim it on screen from this demo.

---

## Demo 3 — Cut off, and the run that stops itself

**What it shows.** One bad setting, a too-small output limit, breaks every reply. The
program checks *why* the model stopped before it reads anything. After three failures out
of three, the batch gives up on purpose. (Objective 1.4: handle a validation failure.)

**When in the lesson.** After paragraph 47, at the end of slide 8, "Set aside, or stop the
run". It also pays off the first failure card on slide 5, the reply cut off halfway. Say so
when it lands.

**Setup.** As Demo 1. About one minute on the test machine.

**What the trainer does.**

1. Say: "Somebody 'saved money' by setting the output limit to 40 tokens. Watch."
2. Show line 151, `# 1. why did it stop? check BEFORE reading the content`. The program
   reads `finish_reason` first.
3. Run:

   ```
   python structured.py batch invoices --max-tokens 40
   ```

4. Point at `finish_reason=length` and the half-object after `reply:`. Then the
   `!!! STOPPING THE RUN` line.

**What the room sees.** Observed:

```text
model qwen3:4b-instruct | 6 invoices | retries 1 | max_tokens 40 | stop if failure rate > 50% after 3 invoices

[inv_3310_mehta.txt]
    call 1: 21.8s, finish_reason=length, reply: {   "amount": 49560.00,   "date": "2026-03-18",   "invoice_number": "331
  -> TRUNCATED  reply cut off at max_tokens=40; nothing to validate
[inv_4471_sharma.txt]
    call 1: 19.8s, finish_reason=length, reply: {   "amount": 42000,   "date": "2026-03-12",   "invoice_number": "4471",  
  -> TRUNCATED  reply cut off at max_tokens=40; nothing to validate
[inv_4472_sharma.txt]
    call 1: 13.9s, finish_reason=length, reply: {   "amount": 11800.0,   "date": "2026-03-13",   "invoice_number": "4472
  -> TRUNCATED  reply cut off at max_tokens=40; nothing to validate

!!! STOPPING THE RUN: 3 of 3 failed (100%) > 50%. 3 invoices not attempted.

>>> 0 in the spreadsheet, 3 set aside for a human, 3 not attempted | 3 model calls, 668 tokens
```

**What it proves.** Strict schema mode did not save these replies. Half an object is not
JSON, so there is nothing to validate. The only honest signal is the stop reason. A
truncated reply is not retried with the error, because the model made no mistake. The
setting did. Three out of three is a pattern, not bad luck. So the job stopped before
paying for the other three.

The trap: people expect "the provider guarantees the schema" to cover this. It covers what
the model is allowed to write, not where the writing is cut off.

**The other two failure cards on slide 5 are not demonstrated.**

- **Refusal.** The program checks `message.refusal` at line 154, before it parses. No
  refusal happened in any run, and no attempt was made to provoke one. It is unproven that
  Ollama ever sets that field. OpenAI's documentation says the field is `refusal`.
  Anthropic signals a refusal with `stop_reason: "refusal"`, not a separate field.
- **A schema rejected by the API.** Ollama accepted every schema sent to it. Showing a 400
  from strict mode needs a hosted key, and none was used.

---

## Demo 4 — Just write the function, then one bounded call

**What it shows.** Part one: on fixed-layout invoices, ten lines of regex do the same job
as the model, with no tokens, in well under a millisecond. Part two: where real judgement
is needed, the model makes one call inside a plain function, and the schema allows exactly
three answers. (Objective 1.7: decide whether an agent is needed, and justify a plain
function.)

**When in the lesson.** Part one after paragraph 28, at the end of slide 10, "Just write
the function". Part two after paragraph 40, on slide 15, "Three tasks, sorted", when the
WhatsApp task is answered.

**Setup.** As Demo 1. Part one took about two minutes on the test machine. Part two took
about three and a half minutes.

**What the trainer does.**

1. Show the paper: `cat system_invoices/BL-26-00781.txt` (`type` in cmd). Say: "Same box,
   same place, every time."
2. Open `structured.py` at line 215, `read_box`. It is a regex and one constructor.
3. Run:

   ```
   python structured.py function-vs-model system_invoices
   ```

4. Read the last two lines aloud. Then point at `same answer: False` on the first invoice,
   and read what differs.
5. At slide 15, open line 257, `def route`. Say: "The order is fixed: receive, classify,
   route. Only the middle step needs a model." Show line 252: the `Literal` with three
   values.
6. Run:

   ```
   python structured.py classify messages.txt
   ```

**What the room sees.** Part one, observed:

```text
[BL-26-00781.txt]
  function :    0.240 ms   0 tokens  BL-26-00781 2026-03-05 28320.0
  model    :    32010 ms 313 tokens  BL-26-00781 2026-03-05 28320.0
  same answer: False  (function, model) -> {'tax': (4320.0, 4320.000000000001)}
[BL-26-00802.txt]
  function :    0.056 ms   0 tokens  BL-26-00802 2026-03-12 11210.0
  model    :    25890 ms 302 tokens  BL-26-00802 2026-03-12 11210.0
  same answer: True
[BL-26-00835.txt]
  function :    0.064 ms   0 tokens  BL-26-00835 2026-03-19 36875.0
  model    :    77415 ms 306 tokens  BL-26-00835 2026-03-19 36875.0
  same answer: True

>>> function total 0.359 ms, 0 tokens | model total 135.3 s, 921 tokens
>>> the model was about 376,817 times slower
```

The paper says `GST 18%: 4320.00`. The model wrote `4320.000000000001`. The function copied
the paper.

Part two, observed:

```text
schema sent: {"additionalProperties": false, "properties": {"label": {"enum": ["complaint", "question", "order"], "title": "Label", "type": "string"}}, "required": ["label"], "title": "Triage", "type": "object"} 

complaint  -> support-team  (21.5s, in 47 out 53 tokens, raw reply 24 chars)  bhai mera order abhi tak nahi aaya 3 din ho gaye ye kya chal raha hai
order      -> sales-desk    (70.8s, in 42 out 124 tokens, raw reply 20 chars)  kal tak 20 packet aur bhej do same rate pe, payment UPI se karunga
question   -> faq-bot       (47.3s, in 34 out 8 tokens, raw reply 21 chars)  aapka shop sunday ko khula rehta hai kya
complaint  -> support-team  (3.3s, in 42 out 9 tokens, raw reply 22 chars)  box phata hua aaya aur andar ka maal geela tha, replacement chahiye
question   -> faq-bot       (49.1s, in 30 out 274 tokens, raw reply 25 chars)  GST bill milega kya is order ka
```

The command was run twice. Both runs gave the same five labels, and each label is the one
a person would pick.

**What it proves.** Part one: the model was right on every field that mattered, and still
lost. It was slower by five orders of magnitude, it cost tokens on every invoice, and it
produced a value nobody printed. The function gives the same answer every time, for free.
That is Microsoft's line, now on screen as numbers: *"If you can write a function to handle
the task, do that instead of using an AI agent."*

The slowdown ratio comes from a loaded CPU machine. Do not quote the number. Quote the
shape: milliseconds and zero tokens against seconds and hundreds of tokens.

Part two: the Hinglish messages need judgement no regex has. But the code still owns the
order. There is no loop and no tool. The model cannot answer "maybe", because the schema
has three values. This is the middle case from slide 13: a function with one model call
inside it.

An oddity worth saying if someone asks: Ollama reported 274 output tokens for a reply of 25
characters. That count is what Ollama's `usage` returned. The cause was not investigated.
It is not a number to quote as what classification costs.

The trap: someone in the room asks "why not let an agent do all of it?" The answer is on
the screen. Part one never needed judgement. Part two needed judgement once, in a known
place.

---

## Where the talk and the current documentation differ

Paragraph 35 of the talk says that in strict mode "the minimum length, the pattern, the
maximum value, are mostly not supported". It depends on the provider, as of 2026-10-15:

- **OpenAI** now lists `pattern`, `format`, `minimum`, `maximum`, `exclusiveMinimum`,
  `exclusiveMaximum` and `multipleOf` as supported. `minLength` and `maxLength` are not in
  its supported list. Nesting is up to 10 levels, with up to 5000 properties.
  (https://developers.openai.com/api/docs/guides/structured-outputs)
- **Anthropic** lists `minimum`, `maximum`, `multipleOf`, `minLength` and `maxLength` as
  not supported, with a 400 error if used. `pattern` works for simple regular
  expressions. Its Python SDK helper strips those keywords from the wire schema and checks
  them on the reply instead.
  (https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

The rule the talk teaches still holds everywhere: put the business rules in your own
validator. That is why `structured.py` keeps them in `business_rules` and out of the
schema, so the same class works on every provider. If someone in the room says "OpenAI
supports `maximum` now", they are right. Say so.
