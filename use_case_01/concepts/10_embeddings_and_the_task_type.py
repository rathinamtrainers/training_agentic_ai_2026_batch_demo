"""Text in, 768 numbers out -- and similarity is arithmetic, not magic.

Real gemini-embedding-001 calls: one question, four passages, cosine over the real vectors.
    uv run --project ../demo python 10_embeddings_and_the_task_type.py
"""
import math
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
client = genai.Client()
MODEL, DIMS = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"), int(os.getenv("EMBEDDING_DIMS", "768"))

QUESTION = "water coming through the ceiling from the flat upstairs"
PASSAGES = ["Escape of water from a neighbouring flat is covered. Excess GBP 350.",
            "Damage from gradual seepage over weeks or months is excluded.",
            "Broker commission is settled monthly in arrears.",
            "Error NW-4471 on the broker portal means the policy is mid-term adjusted."]

def embed(texts, task):
    return [e.values for e in client.models.embed_content(
        model=MODEL, contents=texts,
        config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)).embeddings]

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.dist(a, [0] * DIMS) * math.dist(b, [0] * DIMS))

query = embed([QUESTION], "RETRIEVAL_QUERY")[0]
print(f"{MODEL}: {len(query)} numbers for {QUESTION!r}")
print(f"  first five: {[round(v, 5) for v in query[:5]]}")

print("\n=== every passage scored, most similar first")
for score, text in sorted(zip([cosine(query, v) for v in embed(PASSAGES, "RETRIEVAL_DOCUMENT")], PASSAGES),
                          reverse=True):
    print(f"  cosine {score:.3f}  {text}")

as_document = embed([QUESTION], "RETRIEVAL_DOCUMENT")[0]
print(f"\nSame sentence embedded as RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT: cosine"
      f" {cosine(query, as_document):.3f} -- the task_type is part of the meaning.")
print("Note that nothing here scored zero: a vector search hands back its top k, always.")
