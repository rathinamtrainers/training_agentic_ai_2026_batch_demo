"""An ADK agent is a model, an instruction and a tool belt -- and a runner that streams events.

Real google-adk 2.6.3: InMemoryRunner, one turn, every part printed as it arrives.
    uv run --project ../demo python 06_adk_agent_and_its_event_stream.py
"""
import asyncio
import os
import uuid

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

def search_knowledge_base(question: str) -> dict:
    """Search this Claims team's own Northwind documents. Args: question: the user's question."""
    return {"passages": [{"source_file": "01_escape_of_water.md", "clause": "4",
                          "content": "Escape of water from a neighbouring flat is covered. Excess GBP 350."}]}

agent = Agent(name="grounded_answer_service", model=MODEL, tools=[search_knowledge_base],
              instruction="Answer only from the passages the tool returns, and cite every claim"
                          " inline as [source_file §clause]. Two sentences at most.")

async def main() -> None:
    runner, session = InMemoryRunner(agent=agent, app_name="concepts"), uuid.uuid4().hex[:8]
    await runner.session_service.create_session(app_name="concepts", user_id="claims", session_id=session)
    question = types.Content(role="user", parts=[types.Part(text="is water from the flat above covered?")])
    async for event in runner.run_async(user_id="claims", session_id=session, new_message=question):
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.function_call:
                print(f"  [{event.author}] function_call     {part.function_call.name}({dict(part.function_call.args)})")
            elif part.function_response:
                print(f"  [{event.author}] function_response {part.function_response.response}")
            elif part.text and part.text.strip():
                print(f"  [{event.author}] text (final={event.is_final_response()}) {part.text.strip()}")
        if event.usage_metadata:
            print(f"      usage: prompt {event.usage_metadata.prompt_token_count} tokens")
    await runner.close()

asyncio.run(main())
