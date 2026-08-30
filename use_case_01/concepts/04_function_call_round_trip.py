"""The model does not run your code. It ASKS -- and your runtime runs it and hands the result back.

The raw wire: text -> function_call -> function_response -> text, with real Gemini.
    uv run --project ../demo python 04_function_call_round_trip.py
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()

CORPUS = [("01_escape_of_water.md", "4", "Escape of water from a neighbouring flat is covered. Excess GBP 350."),
          ("11_broker_commission.md", "6", "Broker commission is settled monthly in arrears.")]

def search_knowledge_base(question: str) -> dict:            # ordinary Python, in our process
    words = set(question.lower().split())
    return {"passages": [{"source_file": f, "clause": c, "content": t} for f, c, t in CORPUS
                         if words & set(t.lower().split())][:1]}

TOOL = types.Tool(function_declarations=[types.FunctionDeclaration(
    name="search_knowledge_base",
    description="Search this Northwind team's own documents. Search before answering; never answer from memory.",
    parameters=types.Schema(type=types.Type.OBJECT, required=["question"], properties={
        "question": types.Schema(type=types.Type.STRING, description="the user's question, in their own words")}))])

history = [types.Content(role="user", parts=[types.Part(text="is escape of water from a neighbouring flat covered?")])]
config = types.GenerateContentConfig(tools=[TOOL], automatic_function_calling={"disable": True})

while True:
    reply = client.models.generate_content(model=MODEL, contents=history, config=config)
    part = reply.candidates[0].content.parts[-1]
    history.append(reply.candidates[0].content)
    if not part.function_call:
        print(f"MODEL ANSWERS       > {part.text.strip()}")
        break
    print(f"MODEL REQUESTS TOOL > {part.function_call.name}({dict(part.function_call.args)})")
    result = search_knowledge_base(**dict(part.function_call.args))   # <-- WE run it, not the model
    print(f"RUNTIME RETURNS     > {result}")
    history.append(types.Content(role="user", parts=[types.Part.from_function_response(
        name=part.function_call.name, response=result)]))
