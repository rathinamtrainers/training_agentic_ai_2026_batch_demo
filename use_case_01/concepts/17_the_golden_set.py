"""A labelled set turns "retrieval feels better" into a number -- and the number has to be able to move.

Three human-labelled questions, real embeddings, real reranker, scored with the rerank switch off and on.
    uv run --project ../demo python 17_the_golden_set.py
"""
import json
import math
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client, DIMS = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client(), int(os.getenv("EMBEDDING_DIMS", "768"))
EMBED, FLOOR, TOP_K = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"), float(os.getenv("RERANK_FLOOR", "0.3")), 3
CORPUS = {1: "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
          2: "Damage from gradual seepage over weeks or months is excluded.",
          3: "The standard buildings excess is GBP 250.",
          4: "A final response to a complaint is due within eight weeks.",
          5: "Broker commission is settled monthly in arrears."}
GOLDEN = [("my neighbour's washing machine flooded my ceiling -- covered?", 1),   # labelled by a human:
          ("how long do we have to send a final complaint response?", 4),         # the row that answers it
          ("what excess applies to a standard buildings claim?", 3)]
SCHEMA = types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.OBJECT, required=["id", "score"],
    properties={"id": types.Schema(type=types.Type.INTEGER), "score": types.Schema(type=types.Type.NUMBER)}))

def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

def rerank(question, ids):
    prompt = (f"Question: {question}\n" + "\n".join(f"[{i}] {CORPUS[i]}" for i in ids)
              + "\nScore each passage 0.0-1.0 for whether it answers the question.")
    scores = {int(r["id"]): float(r["score"]) for r in json.loads(client.models.generate_content(
        model=MODEL, contents=prompt, config=types.GenerateContentConfig(temperature=0,
        response_mime_type="application/json", response_schema=SCHEMA)).text)}
    return [i for i in sorted(ids, key=lambda i: -scores[i]) if scores[i] >= FLOOR]

stored = dict(zip(CORPUS, embed(list(CORPUS.values()), "RETRIEVAL_DOCUMENT")))
for label, rerank_on in (("RERANK=off", False), ("RERANK=on", True)):
    precision = []
    print(f"\n=== {label}")
    for question, golden in GOLDEN:
        query = embed([question], "RETRIEVAL_QUERY")[0]
        ranked = sorted(stored, key=lambda i: -sum(x * y for x, y in zip(query, stored[i])))[:TOP_K]
        hits = rerank(question, ranked) if rerank_on else ranked
        precision.append(hits.count(golden) / len(hits) if hits else 0.0)
        print(f"  golden [{golden}]  handed to the model {hits}  context precision {precision[-1]:.2f}")
    print(f"  mean context precision over {len(GOLDEN)} labelled questions: {sum(precision) / len(precision):.2f}")
