"""Demo 1 — the core building blocks of an ADK agent, on Vertex AI.

Six concepts, one file:

    Agent        the unit that thinks and acts
    instruction  the system prompt that shapes its behaviour
    model        the LLM behind it (Gemini, served by Vertex AI)
    description  what this agent is good for, for other agents to read
    Runner       what actually executes the agent
    Event        one step of the run, streamed back as it happens

Run it:

    python adk_01_core/core_agent.py
    python adk_01_core/core_agent.py "your own question"
"""

from __future__ import annotations

import asyncio
import os
import sys

# Point the SDK at Vertex AI *before* importing anything that builds a client.
# Vertex uses Application Default Credentials, so there is no API key here:
#     gcloud auth application-default login
# The three variables are *assigned*, not defaulted: a stale machine-wide
# GOOGLE_CLOUD_PROJECT is a classic first-day trap, and it fails with a 403 on
# a project nobody in the room recognises. VERTEX_PROJECT overrides, for
# students working in their own project.
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get(
    "VERTEX_PROJECT", "agentic-ai-2026-demo"
)
os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("VERTEX_LOCATION", "us-central1")

from google.adk.agents import Agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

APP_NAME = "adk_01_core"
USER_ID = "student"


# --- 1. The agent ------------------------------------------------------------
#
# Four arguments, and each one is a concept on its own.
#
#   name         an identifier, not a label: other agents route by this name
#   model        which LLM does the thinking
#   description  a one-liner for *other agents*, used when delegating work
#   instruction  the system prompt, read by *this* agent on every turn
#
# description and instruction are easy to confuse. description faces outwards,
# instruction faces inwards. In a single-agent program only instruction has any
# effect — description starts to matter in demo 3, when agents delegate.

tutor = Agent(
    name="adk_tutor",
    model=MODEL,
    description="Explains Google ADK concepts to students learning agent development.",
    instruction=(
        "You are a patient tutor for a class learning the Google Agent"
        " Development Kit. Answer in at most five short sentences. Use plain"
        " words. Prefer a concrete example over an abstract definition. If a"
        " question is not about agents or ADK, say so in one sentence."
    ),
)


async def ask(runner: InMemoryRunner, session_id: str, question: str) -> None:
    """Send one question and print every Event the run produces."""

    message = types.Content(role="user", parts=[types.Part(text=question)])

    print(f"\n> {question}\n")

    # --- 2. The runner -------------------------------------------------------
    #
    # The agent object is inert. The Runner is what executes it: it loads the
    # session, calls the model, dispatches any tools, and saves the result.
    #
    # --- 3. The events -------------------------------------------------------
    #
    # run_async does not return an answer. It yields Events — one per step of
    # the run. A simple program keeps only the final one; we print all of them,
    # because seeing the stream is the whole point of this demo.
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        text = "".join(
            part.text for part in (event.content.parts if event.content else []) if part.text
        )
        kind = "final" if event.is_final_response() else "partial"
        print(f"  [event author={event.author} {kind}] {text.strip() or '(no text)'}")


async def main() -> None:
    questions = sys.argv[1:] or [
        "What is the difference between an Agent and a Runner in ADK?",
        "And what is an Event?",
    ]

    # InMemoryRunner is the Runner with throwaway session storage bolted on:
    # nothing survives the process exiting. Session 4 swaps this for a database.
    runner = InMemoryRunner(agent=tutor, app_name=APP_NAME)

    # A session is one conversation. Both questions below share this session,
    # which is why the second one can say "And what is an Event?" and be
    # understood — the history is in the session, not in the agent.
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    print(f"model   : {MODEL} (via Vertex AI)")
    print(f"project : {os.environ['GOOGLE_CLOUD_PROJECT']} / {os.environ['GOOGLE_CLOUD_LOCATION']}")
    print(f"agent   : {tutor.name} - {tutor.description}")
    print(f"session : {session.id}")

    for question in questions:
        await ask(runner, session.id, question)


if __name__ == "__main__":
    asyncio.run(main())
