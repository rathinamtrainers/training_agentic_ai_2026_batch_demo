"""Cut on the clause boundary, because a clause is what a citation points at.

One wording cut two ways, both sets embedded with the real gemini-embedding-001, one question.
    uv run --project ../demo python 09_a_chunk_is_a_clause.py
"""
import math
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
client, DIMS = genai.Client(), int(os.getenv("EMBEDDING_DIMS", "768"))
EMBED = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

DOC = """## 3. Gradual seepage
Damage caused by water that has escaped gradually over a period of weeks or months from a
fixed water system is not covered, however it is discovered.
## 4. Escape of water from a neighbouring property
Damage caused by water escaping from a neighbouring flat is covered in full, including the
cost of tracing and accessing the leak. The excess is GBP 350."""
QUESTION = "my upstairs neighbour's washing machine flooded my ceiling -- is that covered?"

starts = [(m.group(1), m.start()) for m in re.finditer(r"^## (\d+)\.", DOC, re.M)]
spans = [(c, s, starts[i + 1][1] if i + 1 < len(starts) else len(DOC)) for i, (c, s) in enumerate(starts)]
clause_cut = [(c, DOC[s:e].strip()) for c, s, e in spans]                          # demo/chunking.py
window_cut = [("+".join(c for c, s, e in spans if s < i + 200 and e > i), DOC[i:i + 200].strip())
              for i in range(0, len(DOC), 200)]                                    # every 200 characters

def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

query = embed([QUESTION], "RETRIEVAL_QUERY")[0]
cosine = lambda v: sum(x * y for x, y in zip(query, v)) / (math.dist(query, [0] * DIMS) * math.dist(v, [0] * DIMS))

for label, chunks in (("clause cut", clause_cut), ("200-char cut", window_cut)):
    scored = sorted(zip([cosine(v) for v in embed([t for _, t in chunks], "RETRIEVAL_DOCUMENT")], chunks),
                    reverse=True)
    print(f"\n=== {label}: {len(chunks)} chunks,"
          f" {sum('+' in c for c, _ in chunks)} of them straddling a clause boundary")
    for score, (clause, text) in scored:
        print(f"  cosine {score:.3f}  cites [wording.md §{clause}]")
        print("      " + text.replace("\n", "\n      "))
