"""Streaming buys latency and costs certainty: the guardrail can only judge an answer that has finished.

A real FastAPI SSE endpoint over a real Gemini token stream, read by a real client, in one process.
    uv run --project ../demo python 18_streaming_and_the_late_verdict.py
"""
import json
import os
import re
import threading
import time

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()
CITATION = re.compile(r"\[[\w\-.]+\.md\s+§[0-9.]+\]")          # demo/guardrails.py
PROMPT = ("You are an insurance expert. In four sentences, explain to a customer whether water"
          " escaping from the flat above is covered and what excess applies.")
app = FastAPI()

@app.get("/ask/stream")                                        # demo/service.py: ask_stream()
def ask_stream():
    def frames():
        answer = ""
        for chunk in client.models.generate_content_stream(model=MODEL, contents=PROMPT):
            if chunk.text:
                answer += chunk.text
                yield f"data: {json.dumps({'type': 'text', 'text': chunk.text})}\n\n"
        grounded = bool(CITATION.search(answer))               # <- the verdict, only possible now
        yield f"data: {json.dumps({'type': 'done', 'grounded': grounded})}\n\n"
    return StreamingResponse(frames(), media_type="text/event-stream")

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8099, log_level="error"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.1)

started = time.monotonic()
with httpx.stream("GET", "http://127.0.0.1:8099/ask/stream", timeout=120) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            frame = json.loads(line[6:])
            print(f"  t+{time.monotonic() - started:5.2f}s  {frame}")
server.should_exit = True
