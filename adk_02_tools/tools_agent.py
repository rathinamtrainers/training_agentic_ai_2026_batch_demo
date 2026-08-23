"""Demo 2 - tools. The same tutor from demo 1, now able to act.

Demo 1 built an agent that could only talk. Everything it said came out of the
model's own memory, which is why it confidently invented a wrong list of "six
core ADK building blocks" when we asked. This demo fixes that by handing it the
syllabus as a *tool*.

Nothing from demo 1 is thrown away. We import its agent and its Vertex AI setup,
and add exactly one argument: `tools`.

New concepts:

    Function tool   a plain Python function the model may call
    Schema          inferred from the type hints and the docstring - no JSON
    ToolContext     the argument that lets a tool read and write session state
    Tool events     the function_call / function_response pair in the stream

Run it:

    uv run python adk_02_tools/tools_agent.py
    uv run python adk_02_tools/tools_agent.py "What is a Runner?"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# The demo lives one directory down, so put the repo root on the path before
# importing demo 1. Importing it is also what configures Vertex AI - that code
# runs at import time, and we do not want a second copy of it here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adk_01_core.core_agent import MODEL, USER_ID, tutor  # noqa: E402

from google.adk.agents import Agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools import ToolContext  # noqa: E402
from google.genai import types  # noqa: E402

APP_NAME = "adk_02_tools"


# --- The syllabus the tutor is allowed to consult ----------------------------

SYLLABUS: dict[str, str] = {
    "agent": "The unit that thinks and acts. An LlmAgent wraps a model with an instruction.",
    "instruction": "The system prompt. Faces inwards: this agent reads it every turn.",
    "model": "Which LLM does the thinking. Here, Gemini served by Vertex AI.",
    "description": "A one-liner for other agents. Faces outwards, and only matters when agents delegate.",
    "runner": "What actually executes the agent: loads the session, calls the model, dispatches tools.",
    "event": "One step of a run. run_async yields these rather than returning an answer.",
    "tool": "A Python function the model may call. Its signature and docstring become the schema.",
}


# --- 1. A function tool ------------------------------------------------------
#
# This is the whole of it: a normal function. No decorator, no registration, no
# hand-written JSON schema.
#
# ADK reads the signature and the docstring to build the schema the model sees,
# which means the docstring is not a comment here - it is the prompt fragment
# that tells the model when to call this. Vague docstring, unused tool.
#
# Returning a dict, rather than a bare string, is the convention. It gives the
# model a place to see failure ("status": "not_found") without you raising an
# exception into the run.


def look_up_concept(concept: str) -> dict:
    """Look up the official course definition of one Google ADK concept.

    Use this instead of answering from memory whenever a student asks what an
    ADK term means. The course definition is authoritative; your own recall of
    ADK is not.

    Args:
        concept: The ADK term to look up, for example "runner" or "event".

    Returns:
        A dict with "status", and either "definition" or the list of "known"
        concepts when the term is not in the syllabus.
    """
    hit = SYLLABUS.get(concept.strip().lower())
    if hit is None:
        return {"status": "not_found", "known": sorted(SYLLABUS)}
    return {"status": "ok", "concept": concept, "definition": hit}


# --- 2. A tool that uses ToolContext -----------------------------------------
#
# Add a `tool_context: ToolContext` parameter and ADK injects it. The model does
# not see this argument and cannot pass it - it is stripped from the schema.
#
# What it buys you is `tool_context.state`: the session scratchpad. A tool that
# writes to state is how an agent remembers something across turns without that
# something having to sit in the chat history.


def mark_covered(concept: str, tool_context: ToolContext) -> dict:
    """Record that the student has now covered one concept in class.

    Call this after you have explained a concept to the student.

    Args:
        concept: The ADK term that was just explained.

    Returns:
        A dict with "status" and the full "covered" list so far.
    """
    covered = list(tool_context.state.get("covered", []))
    if concept.lower() not in covered:
        covered.append(concept.lower())
    # Assigning to state records a delta on the event. The runner persists it,
    # so the next turn in this session sees the new value.
    tool_context.state["covered"] = covered
    return {"status": "ok", "covered": covered}


# --- 3. The same agent, plus tools -------------------------------------------
#
# Compare this with demo 1. name, model and description are reused verbatim, the
# instruction only grows the paragraph that tells the tutor to prefer the tool
# over its own memory, and `tools` is the one genuinely new argument.

tutor_with_tools = Agent(
    name="adk_tutor_with_tools",
    model=MODEL,
    description=tutor.description,
    instruction=(
        tutor.instruction
        + "\n\nYou have a syllabus tool. Always call look_up_concept before"
        " defining an ADK term, and answer from what it returns rather than"
        " from memory. If the term is not in the syllabus, say so plainly."
        " After you have explained a concept, call mark_covered for it."
    ),
    tools=[look_up_concept, mark_covered],
)


def describe(event) -> list[str]:
    """Turn one Event into readable lines, including the tool traffic."""
    lines: list[str] = []
    for part in event.content.parts if event.content else []:
        if part.function_call:
            lines.append(f"CALL  {part.function_call.name}({dict(part.function_call.args)})")
        elif part.function_response:
            lines.append(f"REPLY {part.function_response.name} -> {part.function_response.response}")
        elif part.text and part.text.strip():
            lines.append(f"TEXT  {part.text.strip()}")
    return lines


async def ask(runner: InMemoryRunner, session_id: str, question: str) -> None:
    message = types.Content(role="user", parts=[types.Part(text=question)])
    print(f"\n> {question}\n")

    # The same loop as demo 1. What changed is what comes out of it: between the
    # question and the answer there are now function_call and function_response
    # events. ADK ran that round trip for us - we never called the tool.
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message
    ):
        for line in describe(event):
            print(f"  [{event.author}] {line}")


async def main() -> None:
    questions = sys.argv[1:] or [
        "What is a Runner in ADK?",
        "And what does description mean?",
        "What have I covered so far?",
    ]

    runner = InMemoryRunner(agent=tutor_with_tools, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    print(f"model   : {MODEL} (via Vertex AI)")
    print(f"agent   : {tutor_with_tools.name}")
    print(f"tools   : {[t.__name__ for t in (look_up_concept, mark_covered)]}")
    print(f"session : {session.id}")

    for question in questions:
        await ask(runner, session.id, question)

    # Proof that mark_covered really wrote to the session, not just to a local
    # variable that vanished when the function returned.
    final = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session.id
    )
    print(f"\nstate['covered'] = {final.state.get('covered')}")


if __name__ == "__main__":
    asyncio.run(main())
