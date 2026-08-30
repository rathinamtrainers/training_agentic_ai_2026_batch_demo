"""A second, more expensive opinion -- and the floor under it is what lets the service refuse.

Real Gemini scoring the candidates hybrid search returned, with the demo's RERANK_FLOOR applied.
    uv run --project ../demo python 13_the_reranker_and_the_floor.py
"""
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()
FLOOR = float(os.getenv("RERANK_FLOOR", "0.3"))

CANDIDATES = {1: "The standard buildings excess is GBP 250.",
              2: "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
              3: "Damage from gradual seepage over weeks or months is excluded.",
              4: "Broker commission is settled monthly in arrears."}
SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(          # demo/rerank.py, verbatim
    type=types.Type.OBJECT, required=["id", "score"], properties={
        "id": types.Schema(type=types.Type.INTEGER), "score": types.Schema(type=types.Type.NUMBER)}))

def rerank(question):
    prompt = (f"You are ranking retrieved passages for relevance to one question.\n\nQuestion: {question}\n\n"
              + "\n".join(f"[{i}] {t}" for i, t in CANDIDATES.items())
              + "\n\nScore each passage 0.0 (irrelevant) to 1.0 (directly answers the question).")
    reply = client.models.generate_content(model=MODEL, contents=prompt, config=types.GenerateContentConfig(
        temperature=0, response_mime_type="application/json", response_schema=SCHEMA))
    return {int(r["id"]): float(r["score"]) for r in json.loads(reply.text)}

for question in ("my upstairs neighbour flooded my ceiling -- am I covered?",
                 "does the policy cover a tropical fish tank?"):
    scores = rerank(question)
    kept = [i for i in sorted(scores, key=scores.get, reverse=True) if scores[i] >= FLOOR]
    print(f"\n=== {question!r}   (floor {FLOOR})")
    for i in sorted(scores, key=scores.get, reverse=True):
        print(f"  {scores[i]:.2f}  {'KEPT   ' if scores[i] >= FLOOR else 'dropped'}  {CANDIDATES[i]}")
    print(f"  -> {len(kept)} passage(s) survive the floor."
          f"{' Retrieval can now say: nothing here.' if not kept else ''}")
