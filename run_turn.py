"""Run one turn through an ADK agent and print everything that happens.

This is the file to have open when the room asks "but what actually happens?".
ADK's runner gives you a stream of EVENTS. Each event has an author (the user,
or an agent) and content made of PARTS. A part is one of three things:

    part.text               the model wrote words
    part.function_call      the model is ASKING for a tool to be run
    part.function_response  the runtime RAN it and is handing the result back

That middle line is session 1's claim made visible: the model requests, the
runtime executes. Nothing here decides to call the tool. We only watch.
"""

import os
import sys
import time
import uuid
from dataclasses import dataclass, field

from google.adk.runners import InMemoryRunner
from google.genai import errors as genai_errors
from google.genai import types

import config

APP_NAME = "session_02"

# Set SESSION02_TRACEBACK=1 to get the real 300-line async traceback back.
# Useful when you are debugging; ruinous when a cohort is watching.
SHOW_TRACEBACKS = os.environ.get("SESSION02_TRACEBACK") == "1"


@dataclass
class Turn:
    text: str = ""
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)
    tool_results: list[tuple[str, object]] = field(default_factory=list)
    elapsed_seconds: float = 0.0


async def ask(agent, question: str, show_events: bool = True) -> Turn:
    """Send one question. Return what came back and what happened on the way.

    A fresh session every time, on purpose: these demos must not inherit
    history from the previous run, or the temperature demo measures the wrong
    thing entirely.
    """
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session_id = f"turn-{uuid.uuid4().hex[:8]}"
    turn = Turn()

    if show_events:
        print(f"\n  USER > {question}")

    started = time.monotonic()
    try:
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id="demo_user", session_id=session_id
        )
        message = types.Content(role="user", parts=[types.Part(text=question)])

        async for event in runner.run_async(
            user_id="demo_user", session_id=session_id, new_message=message
        ):
            for part in (event.content.parts if event.content and event.content.parts else []):
                if part.function_call:
                    call = part.function_call
                    turn.tool_calls.append((call.name, dict(call.args or {})))
                    if show_events:
                        print(f"  MODEL REQUESTS TOOL > {call.name}({_args(call.args)})")
                        print("        ^ the model did not answer. It asked.")
                elif part.function_response:
                    response = part.function_response
                    turn.tool_results.append((response.name, response.response))
                    if show_events:
                        print(f"  RUNTIME RETURNS     > {response.name} -> {response.response}")
                elif part.text and part.text.strip():
                    # The last text the agent writes is the answer. We keep
                    # every one rather than trusting a single flag, because an
                    # empty answer on stage is worse than a redundant line.
                    turn.text = part.text.strip()
                    if show_events:
                        label = "AGENT" if event.is_final_response() else f"({event.author})"
                        print(f"  {label} > {turn.text}")
    except genai_errors.APIError as error:
        # ONLY the API's own errors are caught here. A TypeError in the demo
        # code still explodes with a full traceback, because that one is a real
        # bug and hiding it would be worse.
        if SHOW_TRACEBACKS:
            raise
        _explain_api_error(error)
    finally:
        turn.elapsed_seconds = time.monotonic() - started
        await runner.close()

    return turn


def _args(args) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in (args or {}).items())


# The three things that actually go wrong on a Sunday night, and what to do
# about each. Keyed by HTTP status code from the API.
_LIKELY_CAUSES = {
    404: [
        "The model name is retired or wrong. This is the common one: a name can",
        "still appear in models.list() and yet refuse new keys. Put a current",
        "name in GEMINI_MODEL in .env -- README.md names the pinned one.",
    ],
    400: [
        "The request was rejected. Usually a bad API key, or a model that does",
        "not accept something we sent. Run 00_check_environment.py first.",
    ],
    401: ["The API key is missing, wrong, or not enabled for this model."],
    403: ["The key is not permitted to use this model, or billing is not on."],
    429: [
        "Rate limit or quota. Wait a moment and re-run, or use a project with",
        "quota. Free-tier keys trip this quickly when a demo loops.",
    ],
    500: ["The provider had a server error. Re-run it once before doing anything else."],
    503: ["The model is overloaded at the provider's end. Re-run, or fall back."],
}


def _explain_api_error(error: genai_errors.APIError) -> None:
    """Six lines instead of three hundred.

    Same standard as uc1_service.py: a stack trace in front of a room teaches
    "the demo is broken", which is never the lesson. The API's own message is
    printed verbatim -- we explain it, we never replace it.
    """
    code = getattr(error, "code", None)
    print("\n" + "=" * 72)
    print("THE MODEL CALL FAILED. This is the API refusing, not a bug in the demo.")
    print("=" * 72)
    print(f"  model    {config.model_label()}")
    print(f"  status   {code} {getattr(error, 'status', '') or ''}".rstrip())
    print(f"  message  {getattr(error, 'message', None) or error}")
    print("\n  Most likely:")
    for line in _LIKELY_CAUSES.get(code, ["Read the message above -- it is the API's own words."]):
        print(f"    {line}")
    print("\n  If the API is down altogether, the offline fallback is in README.md:")
    print("    uv sync --extra ollama, `ollama serve`, then MODEL_BACKEND=ollama in .env")
    print("\n  Full traceback, if you actually want it:  SESSION02_TRACEBACK=1 uv run ...")
    print("=" * 72)
    sys.exit(1)
