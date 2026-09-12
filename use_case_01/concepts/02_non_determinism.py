"""The same question twice is two answers -- and temperature 0 is not a promise.

Eight real calls: five at temperature 1.0, three at temperature 0.0.
    uv run --project ../demo python 02_non_determinism.py
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()

PASSAGE = ("[01_escape_of_water.md §4] Escape of water from a neighbouring flat is covered."
           " The excess is GBP 350 and the claim must be notified within 30 days.")
PROMPT = ("Answer this Claims question in one sentence from the passage below, citing"
          f" [file §clause].\n\n{PASSAGE}\n\nQuestion: my upstairs neighbour's washing"
          " machine flooded my ceiling -- am I covered, and what do I pay?")

for temperature, samples in ((1.0, 5), (0.0, 3)):
    answers = []
    print(f"\n=== temperature {temperature}, {samples} calls to {MODEL}")
    for run in range(1, samples + 1):
        reply = client.models.generate_content(
            model=MODEL, contents=PROMPT,
            config=types.GenerateContentConfig(temperature=temperature))
        answers.append(reply.text.strip())
        print(f"  [{run}] {answers[-1]}")
    print(f"  -> {len(set(answers))} distinct answer(s) out of {samples}")

print("\nEvery run is a fresh sample. Assert the shape of what you do not control,"
      "\nand the exact wording only of the sentence you wrote yourself.")
