"""The service layer: FastAPI in front of the agent, with streaming.

Started by 05_serve.py. Two endpoints, and the difference between them is a
teaching point rather than a feature list.

    POST /ask          waits, runs both guardrails, returns one JSON object.
    POST /ask/stream   sends server-sent events as they happen: the tool call,
                       then the answer as it is written, then a verdict.

**The tenant comes from the request's identity, never from the question.** In
Northwind it is the caller's team in Entra ID; here it is the X-Northwind-Team
header, which is the same shape with the identity provider stubbed. If the
tenant could be named in the body, a well-written question would be able to
change it, and every guarantee in this use case would be decoration.

**The honest cost of streaming, said out loud.** The output guardrail can only
judge a finished answer. On /ask/stream the caller has already seen the words
by the time the verdict arrives, so the last event may say "blocked" about text
already on the screen. That is a real trade -- latency against certainty --
and the fix (buffer, judge, then release) is a decision, not an oversight.
"""

import json
import time

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import agent as agent_module
import config
import guardrails
import usage

app = FastAPI(
    title="SageDesk -- Grounded Answer Service (UC1)",
    description="Northwind Assurance. Ask a question, get an answer from your own team's documents.",
    version="1.0.0",
)


class Question(BaseModel):
    question: str
    # Deliberately absent: tenant_id. See the module docstring.


def tenant_from_identity(header: str | None) -> str:
    """The Entra ID stand-in. One header, one lookup, no inference."""
    tenant = (header or config.DEFAULT_TENANT).strip()
    if tenant not in config.TENANTS:
        raise HTTPException(
            status_code=403,
            detail=f"X-Northwind-Team must be one of {', '.join(config.TENANTS)}",
        )
    return tenant


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": config.CHAT_MODEL,
        "backend": config.BACKEND,
        "rerank": config.RERANK,
        "tenants": list(config.TENANTS),
    }


@app.post("/ask")
async def ask(body: Question, x_northwind_team: str | None = Header(default=None)) -> dict:
    tenant = tenant_from_identity(x_northwind_team)
    answer = await agent_module.answer(body.question, tenant_id=tenant, verbose=False)
    return {
        "tenant": tenant,
        "question": body.question,
        "answer": answer.text,
        "citations": [{"source_file": f, "clause": c} for f, c in answer.citations],
        "blocked": answer.blocked,
        "model": answer.model,
        "tokens": {"prompt": answer.prompt_tokens, "output": answer.output_tokens},
        "cost_usd": usage.cost_usd(answer.model, answer.prompt_tokens, answer.output_tokens),
        "elapsed_seconds": round(answer.elapsed_seconds, 2),
    }


@app.post("/ask/stream")
async def ask_stream(body: Question, x_northwind_team: str | None = Header(default=None)):
    tenant = tenant_from_identity(x_northwind_team)

    async def sse():
        started = time.monotonic()

        def send(kind: str, payload: dict) -> str:
            return f"event: {kind}\ndata: {json.dumps(payload)}\n\n"

        try:
            question = guardrails.check_question(body.question)   # <-- guardrail IN
        except guardrails.Blocked as blocked:
            yield send("blocked", {"stage": "input", "reason": str(blocked)})
            return

        yield send("start", {"tenant": tenant, "model": config.CHAT_MODEL})

        collected = ""
        prompt_tokens = output_tokens = 0
        async for event in turn_events(tenant, question):
            if event["type"] == "usage":
                # The meter, on the streaming path too. An answer whose cost is
                # only visible on the non-streaming endpoint is an answer whose
                # cost nobody looks at.
                prompt_tokens += event["prompt_tokens"]
                output_tokens += event["output_tokens"]
                yield send("usage", {"prompt_tokens": prompt_tokens,
                                     "output_tokens": output_tokens})
            elif event["type"] == "tool_call":
                yield send("tool_call", {"name": event["name"], "args": event["args"]})
            elif event["type"] == "tool_result":
                yield send("tool_result", {"passages": event["passages"]})
            elif event["type"] == "text":
                collected = event["text"] if event["partial"] is False else collected + event["text"]
                yield send("text", {"text": event["text"], "partial": event["partial"]})
            elif event["type"] == "error":
                yield send("error", {"message": event["message"]})
                return

        # <-- guardrail OUT, on the finished answer, after the caller has
        # already seen it. The trade is in the module docstring.
        try:
            guardrails.check_answer(collected, tenant)
            verdict = {"grounded": True,
                       "citations": [{"source_file": f, "clause": c}
                                     for f, c in guardrails.citations_in(collected)]}
        except guardrails.Blocked as blocked:
            verdict = {"grounded": False, "reason": str(blocked)}

        verdict["elapsed_seconds"] = round(time.monotonic() - started, 2)
        verdict["tokens"] = {"prompt": prompt_tokens, "output": output_tokens}
        verdict["cost_usd"] = usage.cost_usd(config.CHAT_MODEL, prompt_tokens, output_tokens)
        yield send("done", verdict)

    return StreamingResponse(sse(), media_type="text/event-stream")


async def turn_events(tenant: str, question: str):
    """The agent's event stream, built for this tenant only."""
    import turn

    built = agent_module.build_agent(tenant)
    async for event in turn.events(built, question, stream_tokens=True):
        yield event
