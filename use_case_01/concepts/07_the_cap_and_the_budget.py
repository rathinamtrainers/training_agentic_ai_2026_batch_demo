"""An agent decides when it is finished, so something else has to decide when it is not allowed to continue.

A real Gemini loop over a retriever that genuinely finds nothing, with a tool-call cap and a token budget.
    uv run --project ../demo python 07_the_cap_and_the_budget.py
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()
MAX_TOOL_CALLS, TOKEN_BUDGET = 4, 6000          # demo/turn.py's cap; the budget is the second ceiling

TOOL = types.Tool(function_declarations=[types.FunctionDeclaration(
    name="search_knowledge_base", description="Search this team's own Northwind documents.",
    parameters=types.Schema(type=types.Type.OBJECT, required=["question"], properties={
        "question": types.Schema(type=types.Type.STRING)}))])
config = types.GenerateContentConfig(
    tools=[TOOL], automatic_function_calling={"disable": True},
    system_instruction="Answer only from the search tool. If a search returns no passages,"
                       " search again with different wording until you find something.")

history = [types.Content(role="user", parts=[types.Part(text="what is Northwind's cover for tropical fish?")])]
calls, spent = 0, 0
while True:
    reply = client.models.generate_content(model=MODEL, contents=history, config=config)
    spent += reply.usage_metadata.total_token_count
    history.append(reply.candidates[0].content)
    part = reply.candidates[0].content.parts[-1]
    if not part.function_call:
        print(f"MODEL ANSWERS   > {part.text.strip()}")
        break
    calls += 1
    print(f"TOOL CALL {calls:>2}    > {dict(part.function_call.args)}   [{spent} tokens spent]")
    if calls >= MAX_TOOL_CALLS or spent > TOKEN_BUDGET:
        print(f"STOPPED         > cap={MAX_TOOL_CALLS} calls, budget={TOKEN_BUDGET} tokens."
              f" Used {calls} calls and {spent} tokens. The user gets a refusal, not a bill.")
        break
    history.append(types.Content(role="user", parts=[types.Part.from_function_response(
        name="search_knowledge_base", response={"passages": []})]))   # the corpus really has nothing
