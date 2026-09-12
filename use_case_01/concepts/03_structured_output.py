"""Ask for data, not prose: a response schema is enforced by the API, a regex over prose is hope.

The same reranking job asked twice of the real model -- once free-form, once schema-constrained.
    uv run --project ../demo python 03_structured_output.py
"""
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()

PASSAGES = {1: "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
            2: "Broker commission is settled monthly in arrears.",
            3: "Damage from gradual seepage over weeks or months is excluded."}
PROMPT = ("Score each passage 0.0-1.0 for how well it answers the question."
          " Question: is water from the flat above covered?\n"
          + "\n".join(f"[{i}] {t}" for i, t in PASSAGES.items()))

# demo/rerank.py's schema, exactly: one {id, score} object per passage.
SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(
    type=types.Type.OBJECT, required=["id", "score"], properties={
        "id": types.Schema(type=types.Type.INTEGER),
        "score": types.Schema(type=types.Type.NUMBER)}))

prose = client.models.generate_content(model=MODEL, contents=PROMPT + "\nReply as text.")
print("=== free-form reply, verbatim\n" + prose.text.strip())
print("  regex over it ->", dict(re.findall(r"\[?(\d)\]?[^0-9]{0,20}(0\.\d+)", prose.text)))

typed = client.models.generate_content(
    model=MODEL, contents=PROMPT,
    config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                       response_schema=SCHEMA))
print("\n=== schema-constrained reply, verbatim\n" + typed.text.strip())
print("  json.loads   ->", {r["id"]: r["score"] for r in json.loads(typed.text)})
