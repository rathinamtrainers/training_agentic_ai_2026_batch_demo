# 18 — Streaming and the late verdict

`../18_streaming_and_the_late_verdict.py`

## Summary

The last script in the sequence, and it puts two earlier lessons in direct
conflict.

Streaming is good for the user: tokens appear as they are generated, so the
perceived wait collapses from several seconds to a few hundred milliseconds.
Script 16's guardrail is good for the user too: no answer reaches them unless
every citation in it resolves.

You cannot have both in full. The guardrail judges a finished answer, and a
stream shows the answer before it is finished. By the time the verdict exists,
the user has already read the text.

The script builds the whole thing in one process — a real FastAPI SSE endpoint
over a real Gemini token stream, read by a real `httpx` client — and prints each
frame with the elapsed time in front of it. The output is the argument: a column
of `text` frames arriving early, and one `done` frame at the end carrying
`grounded: false`. The verdict is correct, and it is late.

The prompt is deliberately the ungrounded one from script 16's third run, so
`grounded` comes back `false` and the problem is visible rather than theoretical.

---

## Aspect by aspect

### 1. Everything in one process

```python
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8099, log_level="error"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.1)
```

Server and client in the same script, so the demonstration is one command with
nothing to set up. `daemon=True` means the thread dies with the process;
`server.should_exit = True` at the end asks it to stop cleanly.

The `while not server.started` poll is the small necessary detail — the thread
starts asynchronously, and connecting before the socket is listening fails.
`log_level="error"` keeps uvicorn's startup banner out of the output, which
matters when the output *is* the lesson.

Port 8099, deliberately not the service's own `PORT=8080`, so this can run while
`demo/05_serve.py` is up.

### 2. Server-Sent Events, by hand

```python
@app.get("/ask/stream")                                        # demo/service.py: ask_stream()
def ask_stream():
    def frames():
        ...
            yield f"data: {json.dumps({'type': 'text', 'text': chunk.text})}\n\n"
    return StreamingResponse(frames(), media_type="text/event-stream")
```

SSE is a small enough protocol to write out: each message is `data: ` followed by
a payload and terminated by a **blank line** — hence `\n\n`. Miss one newline and
the client buffers forever.

`media_type="text/event-stream"` is what tells the client and any proxy in
between not to buffer the response.

A generator function passed to `StreamingResponse` is the whole mechanism. FastAPI
consumes it lazily, so a `yield` becomes a frame on the wire.

Each frame carries a `type`. That discriminator is what lets one channel carry
several kinds of message — here `text` and `done`, and in the real service also
errors and citations. Typing the frames from the first version costs nothing and
avoids a protocol change later.

### 3. The model stream

```python
        for chunk in client.models.generate_content_stream(model=MODEL, contents=PROMPT):
            if chunk.text:
                answer += chunk.text
                yield f"data: ..."
```

`generate_content_stream` instead of `generate_content` — the only difference at
the model API level. It yields chunks as they are decoded.

`if chunk.text` is a required guard, not defensive habit: chunks can arrive
carrying only metadata, or a function call, or nothing usable, and `chunk.text`
is then `None`.

`answer += chunk.text` is the crucial line. The full answer is accumulated
server-side *while* it is being streamed out, because the guardrail needs the
whole text and the whole text does not exist anywhere else. The stream is
consumed once; if you do not keep it, it is gone.

### 4. The late verdict

```python
        grounded = bool(CITATION.search(answer))               # <- the verdict, only possible now
        yield f"data: {json.dumps({'type': 'done', 'grounded': grounded})}\n\n"
```

One line, and the comment on it is the title of the script.

`CITATION` is script 16's pattern, simplified. It cannot run earlier: a citation
may be the last four words of the answer, so any check on a partial answer would
report `false` for a perfectly grounded response. The guardrail is a function of
the *complete* text, and completeness is exactly what streaming trades away.

So `grounded` ships as a trailing frame. The client has already rendered the
text. The verdict arrives after the thing it judges.

### 5. What the client does with it

```python
with httpx.stream("GET", "http://127.0.0.1:8099/ask/stream", timeout=120) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            frame = json.loads(line[6:])
            print(f"  t+{time.monotonic() - started:5.2f}s  {frame}")
```

`httpx.stream` as a context manager, `iter_lines()` to read frames as they
arrive. `line[6:]` strips the `data: ` prefix. Blank lines are skipped by the
`startswith` check.

`time.monotonic()` rather than `time.time()` — the correct clock for measuring an
interval, immune to system clock adjustments.

The timestamps are the whole output. Expect the first `text` frame within a few
hundred milliseconds and the `done` frame seconds later. That gap is what
streaming bought, and it is also exactly the window in which an ungrounded answer
was on the user's screen unchallenged.

### 6. The choice the script leaves you with

The script does not resolve the tension, and it should not — it is a product
decision, not a technical one. The options, in the order they usually get
considered:

**Stream, then correct.** Show the text, and on a `grounded: false` verdict
replace it with the refusal. Fastest, and the user briefly saw something the
service has now retracted. For an internal tool with a visible "checking…"
indicator this is often acceptable; for customer-facing advice it usually is not.

**Buffer, then release.** Do not stream to the user at all. Run the guardrail and
send the answer or the refusal. This is what `demo/service.py`'s non-streaming
endpoint does, and it is the right default for regulated content — the latency is
the price of never showing an unverified answer.

**Stream the safe part.** Stream a "searching…" state and the citations as
retrieval resolves them, buffer only the generated prose. More work, and it gives
the user progress without exposing an unchecked claim.

Whichever is chosen, the frame protocol above supports it — which is why the
`type` field was there from the start.

---

## What to take away

- Streaming trades certainty for latency. That is the trade, stated plainly.
- A guardrail is a function of the complete answer. There is no partial verdict.
- Accumulate the full text server-side as you stream it; the stream is consumed
  once.
- Type your frames from the first version — `text`, `done`, and whatever comes
  later.
- Decide deliberately whether an unverified answer may appear on screen. For
  regulated content, buffer.
- SSE is `data: ` plus a payload plus a blank line, with
  `media_type="text/event-stream"`. Nothing more.

## Related

- `16_a_citation_you_can_open.py` — the guardrail being deferred, and the prompt
  reused here.
- `06_adk_agent_and_its_event_stream.py` — the event stream this exposes over
  HTTP.
- `demo/service.py`, `demo/06_stream_client.py` — the shipping endpoint and
  client.
- `../run_logs/18_streaming_and_the_late_verdict_RUN_LOG.md` — recorded runs.
