"""Run one turn through an ADK agent and watch everything that happens.

This is the file to have open when the room asks "but what ACTUALLY happens?".
ADK's runner gives you a stream of EVENTS. Each event has an author and content
made of PARTS, and a part is one of three things:

    part.text               the model wrote words
    part.function_call      the model is ASKING for a tool to be run
    part.function_response  the runtime RAN it and is handing the result back

That middle line is the claim of the whole module made visible: the model
requests, the runtime executes. Nothing in this file decides to call the tool.
We only watch.

It also carries the iteration cap. An agent will keep calling its tool for as
long as it wants to; MAX_TOOL_CALLS is the stop condition that turns a runaway
into a printed refusal instead of a bill. One tool is a small blast radius --
UC2's agent has several, and this is where the habit starts.

Everything that talks to the agent -- the demo scripts, the FastAPI service,
the acceptance tests -- goes through `events()` here, so there is exactly one
place where an ADK event stream is interpreted.
"""

import dataclasses
import sys
import time
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import errors as genai_errors
from google.genai import types

import config

APP_NAME = "sagedesk_uc1"

# A grounded answer needs one search. Two is a rephrase. Five is a loop.
MAX_TOOL_CALLS = int(config.optional("MAX_TOOL_CALLS", "4"))

# Token-level streaming. ADK asks for it through RunConfig; if this import ever
# moves, the service still works and streams whole messages instead, and says
# so rather than pretending.
try:
    from google.adk.agents.run_config import RunConfig, StreamingMode

    STREAMING_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the installed ADK
    STREAMING_AVAILABLE = False


@dataclasses.dataclass
class Turn:
    text: str = ""
    tool_calls: list[tuple[str, dict]] = dataclasses.field(default_factory=list)
    prompt_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0
    capped: bool = False


async def events(agent, question: str, stream_tokens: bool = False):
    """Yield one small dict per thing that happens. The only ADK-shaped code.

    A fresh session every time, on purpose: these are single-turn questions, and
    inheriting the previous demo's history would make the next answer a
    coincidence.
    """
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session_id = f"turn-{uuid.uuid4().hex[:8]}"
    message = types.Content(role="user", parts=[types.Part(text=question)])
    calls = 0

    kwargs = {}
    if stream_tokens and STREAMING_AVAILABLE:
        kwargs["run_config"] = RunConfig(streaming_mode=StreamingMode.SSE)

    try:
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id="demo_user", session_id=session_id
        )
        async for event in runner.run_async(
            user_id="demo_user", session_id=session_id, new_message=message, **kwargs
        ):
            usage = getattr(event, "usage_metadata", None)
            if usage:
                yield {
                    "type": "usage",
                    "prompt_tokens": usage.prompt_token_count or 0,
                    "output_tokens": usage.candidates_token_count or 0,
                }

            for part in (event.content.parts if event.content and event.content.parts else []):
                if part.function_call:
                    calls += 1
                    yield {
                        "type": "tool_call",
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args or {}),
                    }
                    if calls > MAX_TOOL_CALLS:
                        yield {"type": "capped", "limit": MAX_TOOL_CALLS}
                        return
                elif part.function_response:
                    passages = (part.function_response.response or {}).get("passages", [])
                    yield {"type": "tool_result", "passages": len(passages)}
                elif part.text and part.text.strip():
                    yield {
                        "type": "text",
                        "text": part.text,
                        "final": bool(event.is_final_response()),
                        "partial": bool(getattr(event, "partial", False)),
                    }
    except genai_errors.APIError as error:
        # ONLY the API's own errors are caught here. A TypeError in this code
        # still explodes with a full traceback, because that one is a real bug
        # and hiding it would be worse.
        yield {"type": "error", "message": _api_error_text(error)}
    finally:
        await runner.close()


async def run(agent, question: str, verbose: bool = True) -> Turn:
    """Collect a whole turn, printing it as it happens."""
    turn = Turn()
    started = time.monotonic()

    if verbose:
        print(f"\n  USER > {question}")

    async for event in events(agent, question):
        kind = event["type"]
        if kind == "usage":
            turn.prompt_tokens += event["prompt_tokens"]
            turn.output_tokens += event["output_tokens"]
        elif kind == "tool_call":
            turn.tool_calls.append((event["name"], event["args"]))
            if verbose:
                print(f"  MODEL REQUESTS TOOL > {event['name']}({_args(event['args'])})")
                print("        ^ the model did not answer. It asked.")
        elif kind == "tool_result" and verbose:
            print(f"  RUNTIME RETURNS     > {event['passages']} passages")
        elif kind == "text":
            turn.text = event["text"].strip()
            if verbose and event["final"]:
                print(f"  AGENT > {turn.text}")
        elif kind == "capped":
            turn.capped = True
            print(f"  [cap] {event['limit']} tool calls is the ceiling. Stopping.")
        elif kind == "error":
            print(event["message"])
            sys.exit(1)

    turn.elapsed_seconds = time.monotonic() - started
    return turn


def _args(args) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in (args or {}).items())


# The things that actually go wrong on a Sunday night, keyed by HTTP status.
_LIKELY_CAUSES = {
    400: ["The request was rejected -- usually a bad key, or a model that does",
          "not accept something we sent. Run 00_check_environment.py first."],
    401: ["The API key is missing, wrong, or not enabled for this model."],
    403: ["The key is not permitted to use this model, or billing is off.",
          "On GENAI_BACKEND=vertex this is usually the wrong project."],
    404: ["The model name is retired or wrong. Put a current id in GEMINI_MODEL",
          "in .env -- README.md names the pinned one and its fallback."],
    429: ["Rate limit or quota. Free-tier keys trip this quickly when an ingest",
          "or an eval run loops. Wait, or use a project with quota."],
    500: ["The provider had a server error. Re-run once before doing anything."],
    503: ["The model is overloaded at the provider's end. Re-run."],
}


def _api_error_text(error: genai_errors.APIError) -> str:
    """Six lines instead of three hundred. A stack trace in front of a room
    teaches 'the demo is broken', which is never the lesson. The API's own
    message is quoted verbatim -- we explain it, we never replace it."""
    code = getattr(error, "code", None)
    lines = [
        "",
        "=" * 72,
        "THE MODEL CALL FAILED. This is the API refusing, not a bug in the demo.",
        "=" * 72,
        f"  backend  {config.BACKEND}",
        f"  model    {config.CHAT_MODEL}",
        f"  status   {code} {getattr(error, 'status', '') or ''}".rstrip(),
        f"  message  {getattr(error, 'message', None) or error}",
        "",
        "  Most likely:",
    ]
    lines += [f"    {line}" for line in _LIKELY_CAUSES.get(
        code, ["Read the message above -- it is the API's own words."])]
    lines.append("=" * 72)
    return "\n".join(lines)
